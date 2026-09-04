#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path

from isolated_env import require_isolated_benchmark


require_isolated_benchmark()

from memory.dense_index import rebuild_dense_index
from memory.hybrid_search import hybrid_search
from memory.store import add_message, init_db


CASES = [
    {
        "query": "Where do I go when I want somewhere quiet to focus?",
        "gold": "[SEMANTIC_GOLD]",
    },
    {
        "query": "What identifier does service Kestrel use?",
        "gold": "[EXACT_GOLD]",
    },
    {
        "query": "Where is Project Nightjar's backup cache?",
        "gold": "[HYBRID_GOLD]",
    },
]

FIXTURES = [
    (
        "[SEMANTIC_GOLD] When I need peace and concentration, "
        "I usually work at Juniper Library."
    ),
    (
        "[EXACT_GOLD] Service Kestrel uses identifier KST-7319."
    ),
    (
        "[HYBRID_GOLD] Project Nightjar keeps its backup cache "
        "in Vault N-17."
    ),
    "I bought oranges after work yesterday.",
    "The garden needs watering this weekend.",
]


def main():
    init_db()

    for text in FIXTURES:
        add_message("a0-smoke-fixture", "user", text)

    rebuild = rebuild_dense_index()

    results = []

    for case in CASES:
        retrieved = hybrid_search(case["query"], limit=5)

        rank = next(
            (
                index
                for index, item in enumerate(retrieved, start=1)
                if case["gold"] in item["content"]
            ),
            None,
        )

        results.append({
            "query": case["query"],
            "gold": case["gold"],
            "rank": rank,
            "passed": rank is not None,
            "retrieved_ids": [item["id"] for item in retrieved],
        })

    passed = all(item["passed"] for item in results)

    payload = {
        "benchmark": "a0-production-retrieval-smoke",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rebuild": rebuild,
        "results": results,
        "passed": passed,
    }

    output_dir = Path("benchmarks/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    output_path = (
        output_dir
        / f"a0-production-retrieval-smoke-{timestamp}.json"
    )

    output_path.write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(
            status,
            f'rank={item["rank"]}',
            item["query"],
        )

    print("RESULT_FILE:", output_path)
    print(
        "A0_PRODUCTION_RETRIEVAL_SMOKE:",
        "PASS" if passed else "FAIL",
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
