from sentence_transformers import SentenceTransformer
import numpy as np

from memory.store import connect


MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"


def load_messages():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
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


def semantic_search(query, limit=5):
    messages = load_messages()

    if not messages:
        return []

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu",
        trust_remote_code=True,
    )

    query_vector = model.encode(
        query,
        normalize_embeddings=True,
    )

    message_vectors = model.encode(
        [message["content"] for message in messages],
        normalize_embeddings=True,
    )

    results = []

    for message, vector in zip(messages, message_vectors):
        score = float(np.dot(query_vector, vector))

        results.append({
            **message,
            "score": score,
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:limit]


if __name__ == "__main__":
    query = "What bird did I say I liked?"

    print("QUERY:", query)
    print()

    for rank, item in enumerate(
        semantic_search(query, limit=5),
        start=1,
    ):
        print(
            rank,
            f'{item["score"]:.4f}',
            f'#{item["id"]}',
            item["role"],
            item["content"],
        )
