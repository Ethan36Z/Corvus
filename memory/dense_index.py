from functools import lru_cache
import hashlib
from pathlib import Path

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

from memory.store import connect


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LANCE_DB_PATH = PROJECT_ROOT / "data" / "corvus-retrieval.lancedb"
TABLE_NAME = "evidence_dense_v1"

MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"
MODEL_REVISION = "ca1791e0bcc104f6db161f27de1340241b13c5a4"

EMBEDDING_DIM = 768
INDEX_SCHEMA_VERSION = 1


DENSE_SCHEMA = pa.schema([
    pa.field("message_id", pa.int64()),
    pa.field("session_id", pa.string()),
    pa.field("role", pa.string()),
    pa.field("created_at", pa.string()),

    pa.field("content_sha256", pa.string()),

    pa.field("embedding_model", pa.string()),
    pa.field("embedding_revision", pa.string()),
    pa.field("embedding_dim", pa.int32()),
    pa.field("schema_version", pa.int16()),

    pa.field(
        "vector",
        pa.list_(
            pa.float32(),
            EMBEDDING_DIM,
        ),
    ),
])


def content_sha256(content):
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def load_embedding_model():
    return SentenceTransformer(
        MODEL_NAME,
        revision=MODEL_REVISION,
        device="cpu",
        trust_remote_code=True,
    )


def load_source_messages():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                session_id,
                role,
                content,
                created_at
            FROM messages
            ORDER BY id ASC
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def make_index_row(message, vector):
    if len(vector) != EMBEDDING_DIM:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"expected {EMBEDDING_DIM}, "
            f"got {len(vector)}"
        )

    return {
        "message_id": message["id"],
        "session_id": message["session_id"],
        "role": message["role"],
        "created_at": message["created_at"],

        "content_sha256": content_sha256(
            message["content"]
        ),

        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "embedding_dim": EMBEDDING_DIM,
        "schema_version": INDEX_SCHEMA_VERSION,

        "vector": vector,
    }


def rebuild_dense_index(batch_size=64):
    """
    Deterministically rebuild the entire derived dense index
    from the canonical SQLite Evidence Log.

    This function is intentionally explicit and destructive:
    the LanceDB table is recreated from source evidence.
    """

    messages = load_source_messages()

    db = lancedb.connect(
        str(LANCE_DB_PATH)
    )

    table = db.create_table(
        TABLE_NAME,
        schema=DENSE_SCHEMA,
        mode="overwrite",
    )

    if not messages:
        return {
            "source_messages": 0,
            "indexed_messages": 0,
            "table_rows": 0,
        }

    model = load_embedding_model()

    indexed = 0

    for start in range(
        0,
        len(messages),
        batch_size,
    ):
        batch = messages[
            start:start + batch_size
        ]

        texts = [
            message["content"]
            for message in batch
        ]

        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        rows = [
            make_index_row(
                message,
                vector.tolist(),
            )
            for message, vector
            in zip(batch, vectors)
        ]

        arrow_batch = pa.Table.from_pylist(
            rows,
            schema=DENSE_SCHEMA,
        )

        (
            table
            .merge_insert("message_id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(arrow_batch)
        )

        indexed += len(rows)

    return {
        "source_messages": len(messages),
        "indexed_messages": indexed,
        "table_rows": table.count_rows(),
    }


def dense_index_status():
    db = lancedb.connect(
        str(LANCE_DB_PATH)
    )

    try:
        table = db.open_table(
            TABLE_NAME
        )
    except Exception:
        return {
            "exists": False,
            "rows": 0,
            "path": str(LANCE_DB_PATH),
            "table": TABLE_NAME,
        }

    return {
        "exists": True,
        "rows": table.count_rows(),
        "path": str(LANCE_DB_PATH),
        "table": TABLE_NAME,
        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "embedding_dim": EMBEDDING_DIM,
        "schema_version": INDEX_SCHEMA_VERSION,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=[
            "status",
            "rebuild",
        ],
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
    )

    args = parser.parse_args()

    if args.command == "status":
        result = dense_index_status()
    else:
        result = rebuild_dense_index(
            batch_size=args.batch_size,
        )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
