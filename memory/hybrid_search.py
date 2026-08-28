from memory.semantic_search import semantic_search
from memory.sparse_search import sparse_search


def hybrid_search(
    query,
    limit=5,
    candidate_limit=20,
    rrf_k=60,
):
    dense_results = semantic_search(
        query,
        limit=candidate_limit,
    )

    sparse_results = sparse_search(
        query,
        limit=candidate_limit,
    )

    fused = {}

    for rank, item in enumerate(dense_results, start=1):
        message_id = item["id"]

        fused[message_id] = {
            **item,
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
