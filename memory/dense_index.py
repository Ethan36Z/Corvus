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


def load_source_messages_by_ids(message_ids):
    """
    Load specific canonical Evidence Log messages from SQLite.

    This is a targeted read used by incremental dense indexing.
    It does not scan the full Evidence Log.
    """
    ids = sorted({
        int(message_id)
        for message_id in message_ids
    })

    if not ids:
        return {}

    if any(message_id <= 0 for message_id in ids):
        raise ValueError(
            "message_ids must be positive integers"
        )

    placeholders = ", ".join(
        "?"
        for _ in ids
    )

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                id,
                session_id,
                role,
                content,
                created_at
            FROM messages
            WHERE id IN ({placeholders})
            """,
            ids,
        ).fetchall()

    return {
        row[0]: {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    }


def load_source_message_ids_after(after_id, limit=64):
    """
    Load only Evidence Log message IDs newer than a contiguous
    indexing progress point.

    This is used by background incremental recovery. It does not load
    message content and does not scan/re-embed historical evidence.
    """
    after_id = int(after_id)
    limit = int(limit)

    if after_id < 0:
        raise ValueError(
            "after_id must be non-negative"
        )

    if limit <= 0:
        raise ValueError(
            "limit must be positive"
        )

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM messages
            WHERE id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (after_id, limit),
        ).fetchall()

    return [
        int(row[0])
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


def load_index_rows_by_ids(message_ids):
    """
    Load dense-index metadata for specific Evidence Log message IDs.

    This is a targeted, read-only lookup used by incremental indexing.
    It does not embed content, scan SQLite history, or mutate LanceDB.
    """
    ids = sorted({
        int(message_id)
        for message_id in message_ids
    })

    if not ids:
        return {}

    if any(message_id <= 0 for message_id in ids):
        raise ValueError(
            "message_ids must be positive integers"
        )

    db = lancedb.connect(
        str(LANCE_DB_PATH)
    )
    table = db.open_table(
        TABLE_NAME
    )

    where_clause = (
        "message_id IN ("
        + ", ".join(str(message_id) for message_id in ids)
        + ")"
    )

    rows = (
        table.search()
        .where(where_clause)
        .select([
            "message_id",
            "content_sha256",
            "embedding_model",
            "embedding_revision",
            "embedding_dim",
            "schema_version",
        ])
        .to_list()
    )

    rows_by_id = {}

    for row in rows:
        message_id = int(
            row["message_id"]
        )

        if message_id in rows_by_id:
            raise RuntimeError(
                "Duplicate dense-index rows for "
                f"message_id={message_id}"
            )

        rows_by_id[message_id] = row

    return rows_by_id


def classify_dense_message_ids(message_ids):
    """
    Classify specific Evidence Log messages against the derived
    dense index without embedding or mutating either data store.

    States:
      current        - derived row matches canonical evidence/config
      missing        - canonical evidence exists but index row does not
      stale          - index row exists but is incompatible/outdated
      source_missing - requested ID does not exist in SQLite
    """
    ids = sorted({
        int(message_id)
        for message_id in message_ids
    })

    if not ids:
        return {
            "current": [],
            "missing": [],
            "stale": [],
            "source_missing": [],
        }

    source_rows = load_source_messages_by_ids(ids)
    index_rows = load_index_rows_by_ids(ids)

    result = {
        "current": [],
        "missing": [],
        "stale": [],
        "source_missing": [],
    }

    for message_id in ids:
        source = source_rows.get(message_id)

        if source is None:
            result["source_missing"].append(message_id)
            continue

        indexed = index_rows.get(message_id)

        if indexed is None:
            result["missing"].append(message_id)
            continue

        expected_hash = content_sha256(
            source["content"]
        )

        compatible = (
            indexed["content_sha256"] == expected_hash
            and indexed["embedding_model"] == MODEL_NAME
            and indexed["embedding_revision"] == MODEL_REVISION
            and indexed["embedding_dim"] == EMBEDDING_DIM
            and indexed["schema_version"] == INDEX_SCHEMA_VERSION
        )

        if compatible:
            result["current"].append(message_id)
        else:
            result["stale"].append(message_id)

    return result


def sync_dense_message_ids(message_ids, batch_size=64):
    """
    Incrementally synchronize specific canonical Evidence Log messages
    into the persistent derived dense index.

    Only missing or stale messages are embedded.
    Current messages are skipped.
    Full rebuild remains the authoritative recovery path.
    """
    if batch_size <= 0:
        raise ValueError(
            "batch_size must be positive"
        )

    classification = classify_dense_message_ids(
        message_ids
    )

    to_index = sorted(
        classification["missing"]
        + classification["stale"]
    )

    if not to_index:
        return {
            "current": classification["current"],
            "missing_before": classification["missing"],
            "stale_before": classification["stale"],
            "source_missing": classification["source_missing"],
            "indexed": 0,
        }

    source_rows = load_source_messages_by_ids(
        to_index
    )

    model = load_embedding_model()

    db = lancedb.connect(
        str(LANCE_DB_PATH)
    )
    table = db.open_table(
        TABLE_NAME
    )

    indexed = 0

    for start in range(
        0,
        len(to_index),
        batch_size,
    ):
        batch_ids = to_index[
            start:start + batch_size
        ]

        messages = [
            source_rows[message_id]
            for message_id in batch_ids
        ]

        texts = [
            message["content"]
            for message in messages
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
            in zip(messages, vectors)
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
        "current": classification["current"],
        "missing_before": classification["missing"],
        "stale_before": classification["stale"],
        "source_missing": classification["source_missing"],
        "indexed": indexed,
    }


def ensure_dense_progress_table():
    """
    Ensure durable operational progress storage exists.

    This table is not Evidence Log content. It records only the
    background dense-index worker's contiguous completion point.
    """
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dense_index_progress (
                index_name TEXT PRIMARY KEY,
                last_message_id INTEGER NOT NULL
                    CHECK (last_message_id >= 0)
            )
            """
        )
        conn.commit()


def get_dense_progress():
    """
    Return the durable contiguous completion point for this dense index.
    """
    ensure_dense_progress_table()

    with connect() as conn:
        row = conn.execute(
            """
            SELECT last_message_id
            FROM dense_index_progress
            WHERE index_name = ?
            """,
            (TABLE_NAME,),
        ).fetchone()

    if row is None:
        return 0

    return int(row[0])


def set_dense_progress(last_message_id):
    """
    Persist the dense worker's contiguous completion point.

    Call this only after the corresponding dense sync has succeeded.
    """
    last_message_id = int(last_message_id)

    if last_message_id < 0:
        raise ValueError(
            "last_message_id must be non-negative"
        )

    ensure_dense_progress_table()

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO dense_index_progress (
                index_name,
                last_message_id
            )
            VALUES (?, ?)
            ON CONFLICT(index_name)
            DO UPDATE SET
                last_message_id = excluded.last_message_id
            """,
            (
                TABLE_NAME,
                last_message_id,
            ),
        )
        conn.commit()


def sync_dense_tail_once(limit=64):
    """
    Process one recoverable batch of Evidence Log messages newer than
    the durable dense-index progress point.

    Progress advances only after the entire requested batch has
    synchronized successfully.
    """
    limit = int(limit)

    if limit <= 0:
        raise ValueError(
            "limit must be positive"
        )

    progress_before = get_dense_progress()

    message_ids = load_source_message_ids_after(
        progress_before,
        limit,
    )

    if not message_ids:
        return {
            "progress_before": progress_before,
            "message_ids": [],
            "indexed": 0,
            "progress_after": progress_before,
        }

    sync_result = sync_dense_message_ids(
        message_ids
    )

    if sync_result["source_missing"]:
        raise RuntimeError(
            "Evidence Log changed during dense tail sync: "
            f"{sync_result['source_missing']}"
        )

    progress_after = message_ids[-1]

    set_dense_progress(
        progress_after
    )

    return {
        "progress_before": progress_before,
        "message_ids": message_ids,
        "indexed": sync_result["indexed"],
        "progress_after": progress_after,
    }


def search_dense_message_ids(
    query,
    limit=5,
    session_id=None,
    role=None,
):
    """
    Search the persistent derived dense index.

    Optional metadata filters are explicit deterministic constraints.
    Returns only message IDs and vector distances.
    Canonical message content must be hydrated from SQLite separately.
    """
    query = str(query).strip()
    limit = int(limit)

    if not query:
        return []

    if limit <= 0:
        raise ValueError(
            "limit must be positive"
        )

    model = load_embedding_model()

    vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    db = lancedb.connect(
        str(LANCE_DB_PATH)
    )
    table = db.open_table(
        TABLE_NAME
    )

    search = table.search(vector)

    filters = []

    if session_id is not None:
        value = str(session_id).replace("'", "''")
        filters.append(
            f"session_id = '{value}'"
        )

    if role is not None:
        value = str(role).replace("'", "''")
        filters.append(
            f"role = '{value}'"
        )

    if filters:
        search = search.where(
            " AND ".join(filters)
        )

    rows = (
        search
        .select([
            "message_id",
            "_distance",
        ])
        .limit(limit)
        .to_list()
    )

    return [
        {
            "message_id": int(row["message_id"]),
            "distance": float(row["_distance"]),
        }
        for row in rows
    ]


def hydrate_dense_search_results(results):
    """
    Hydrate ranked dense-search results from canonical SQLite evidence.

    LanceDB supplies only derived retrieval metadata. Raw message
    content always comes from the SQLite Evidence Log.
    """
    if not results:
        return []

    message_ids = [
        int(result["message_id"])
        for result in results
    ]

    source_rows = load_source_messages_by_ids(
        message_ids
    )

    hydrated = []

    for result in results:
        message_id = int(
            result["message_id"]
        )

        source = source_rows.get(
            message_id
        )

        if source is None:
            # Never expose derived index data as canonical evidence.
            continue

        hydrated.append({
            "message_id": message_id,
            "session_id": source["session_id"],
            "role": source["role"],
            "content": source["content"],
            "created_at": source["created_at"],
            "distance": float(result["distance"]),
        })

    return hydrated


def search_dense_messages(
    query,
    limit=5,
    session_id=None,
    role=None,
):
    """
    Persistent dense Evidence Recall with canonical SQLite hydration.
    """
    results = search_dense_message_ids(
        query,
        limit=limit,
        session_id=session_id,
        role=role,
    )

    return hydrate_dense_search_results(
        results
    )


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
