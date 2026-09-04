from memory.dense_index import search_dense_messages
from memory.sparse_search import sparse_search


def hybrid_search(
    query,
    limit=5,
    candidate_limit=20,
    rrf_k=60,
    session_id=None,
    role=None,
):
    dense_results = search_dense_messages(
        query,
        limit=candidate_limit,
        session_id=session_id,
        role=role,
    )

    sparse_results = sparse_search(
        query,
        limit=candidate_limit,
        session_id=session_id,
        role=role,
    )

    fused = {}

    for rank, item in enumerate(dense_results, start=1):
        message_id = item["message_id"]

        normalized_item = {
            "id": message_id,
            "session_id": item["session_id"],
            "role": item["role"],
            "content": item["content"],
            "created_at": item["created_at"],
            "distance": item["distance"],
        }

        fused[message_id] = {
            **normalized_item,
            "rrf_score": 0.0,
            "dense_rank": None,
            "sparse_rank": None,
        }

        fused[message_id]["dense_rank"] = rank
        fused[message_id]["rrf_score"] += 1.0 / (
            rrf_k + rank
        )

    for rank, item in enumerate(sparse_results, start=1):
        message_id = item["id"]

        if message_id not in fused:
            fused[message_id] = {
                **item,
                "rrf_score": 0.0,
                "dense_rank": None,
                "sparse_rank": None,
            }

        fused[message_id]["sparse_rank"] = rank
        fused[message_id]["rrf_score"] += 1.0 / (
            rrf_k + rank
        )

    results = sorted(
        fused.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return results[:limit]


if __name__ == "__main__":
    query = "What port does Project Magpie use?"

    print("QUERY:", query)
    print()

    for rank, item in enumerate(
        hybrid_search(query, limit=5),
        start=1,
    ):
        print(
            rank,
            f'rrf={item["rrf_score"]:.6f}',
            f'dense={item["dense_rank"]}',
            f'sparse={item["sparse_rank"]}',
            f'#{item["id"]}',
            item["content"],
        )
