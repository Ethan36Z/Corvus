from memory.semantic_search import semantic_search
from memory.sparse_search import sparse_search
from memory.hybrid_search import hybrid_search


CASES = [
    {
        "name": "semantic_paraphrase",
        "query": "Where do I usually go when I want a quiet place to focus?",
        "gold_label": "SEMANTIC_GOLD",
    },
    {
        "name": "exact_identifier",
        "query": "What identifier does service Kestrel use?",
        "gold_label": "EXACT_GOLD",
    },
    {
        "name": "mixed_evidence",
        "query": "Where is the backup cache for Project Nightjar?",
        "gold_label": "HYBRID_GOLD",
    },
]


def find_gold_rank(results, gold_label):
    marker = f"[{gold_label}]"

    for rank, item in enumerate(results, start=1):
        if marker in item["content"]:
            return rank

    return None


def show_results(name, results):
    print(name)

    for rank, item in enumerate(results, start=1):
        print(
            rank,
            f'#{item["id"]}',
            item["content"],
        )

    print()


for case in CASES:
    print("=" * 70)
    print("CASE:", case["name"])
    print("QUERY:", case["query"])
    print()

    dense = semantic_search(
        case["query"],
        limit=10,
    )

    sparse = sparse_search(
        case["query"],
        limit=10,
    )

    hybrid = hybrid_search(
        case["query"],
        limit=10,
    )

    show_results("DENSE", dense)
    show_results("SPARSE", sparse)
    show_results("HYBRID", hybrid)

    print("GOLD RANKS")
    print(
        "Dense:",
        find_gold_rank(dense, case["gold_label"]),
    )
    print(
        "Sparse:",
        find_gold_rank(sparse, case["gold_label"]),
    )
    print(
        "Hybrid:",
        find_gold_rank(hybrid, case["gold_label"]),
    )
    print()
