import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from memory.semantic_search import semantic_search


API_URL = (
    "http:"
    + chr(47)
    + chr(47)
    + "127.0.0.1:8095"
    + chr(47)
    + "v1"
    + chr(47)
    + "chat"
    + chr(47)
    + "completions"
)

CASES = [
    {
        "question": "What is my favorite moon for the Corvus benchmark?",
        "expected": "Callisto",
    },
    {
        "question": "Where is the blue box stored for the Corvus benchmark?",
        "expected": "Cedar Room",
    },
    {
        "question": "What port does Project Lantern use?",
        "expected": "7319",
    },
    {
        "question": "What is my test drink for the Corvus benchmark?",
        "expected": "jasmine tea",
    },
    {
        "question": "What is the raven's nickname for the Corvus benchmark?",
        "expected": "Ember",
    },
]


def call_model(messages):
    payload = {
        "messages": messages,
        "temperature": 0,
        "top_p": 1.0,
        "seed": 42,
        "max_tokens": 256,
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    request_ms = (time.perf_counter() - start) * 1000

    return (
        result["choices"][0]["message"]["content"],
        request_ms,
    )


def run_no_memory(case):
    answer, request_ms = call_model([
        {
            "role": "user",
            "content": case["question"],
        }
    ])

    passed = case["expected"].lower() in answer.lower()

    return {
        "question": case["question"],
        "expected": case["expected"],
        "answer": answer,
        "passed": passed,
        "retrieval_ms": 0.0,
        "request_ms": request_ms,
        "total_ms": request_ms,
        "retrieved_memories": [],
    }


def run_rag(case):
    total_start = time.perf_counter()

    retrieval_start = time.perf_counter()

    memories = semantic_search(
        case["question"],
        limit=3,
    )

    retrieval_ms = (
        time.perf_counter() - retrieval_start
    ) * 1000

    memory_lines = []

    for memory in memories:
        memory_lines.append(
            f'[memory #{memory["id"]} role={memory["role"]}] '
            f'{memory["content"]}'
        )

    memory_context = "\n".join(memory_lines)

    messages = [
        {
            "role": "system",
            "content": (
                "Relevant memories retrieved from the persistent archive:\n"
                + memory_context
                + "\n\nUse these memories when they are relevant "
                  "to the user's question."
            ),
        },
        {
            "role": "user",
            "content": case["question"],
        },
    ]

    answer, request_ms = call_model(messages)

    total_ms = (
        time.perf_counter() - total_start
    ) * 1000

    passed = case["expected"].lower() in answer.lower()

    return {
        "question": case["question"],
        "expected": case["expected"],
        "answer": answer,
        "passed": passed,
        "retrieval_ms": retrieval_ms,
        "request_ms": request_ms,
        "total_ms": total_ms,
        "retrieved_memories": [
            {
                "id": memory["id"],
                "role": memory["role"],
                "content": memory["content"],
                "score": memory["score"],
            }
            for memory in memories
        ],
    }


def main():
    results = {
        "benchmark": "p1-rag-smoke",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": len(CASES),
        "no_memory": [],
        "vanilla_rag": [],
    }

    print("===== NO MEMORY =====")

    for index, case in enumerate(CASES, start=1):
        result = run_no_memory(case)
        results["no_memory"].append(result)

        mark = "PASS" if result["passed"] else "FAIL"

        print(
            f'{index}/5 {mark} '
            f'{result["request_ms"]:.1f} ms '
            f'expected={result["expected"]}'
        )

    print()
    print("===== VANILLA RAG =====")

    for index, case in enumerate(CASES, start=1):
        result = run_rag(case)
        results["vanilla_rag"].append(result)

        mark = "PASS" if result["passed"] else "FAIL"

        print(
            f'{index}/5 {mark} '
            f'retrieval={result["retrieval_ms"]:.1f} ms '
            f'llm={result["request_ms"]:.1f} ms '
            f'total={result["total_ms"]:.1f} ms '
            f'expected={result["expected"]}'
        )

    no_memory_score = sum(
        item["passed"]
        for item in results["no_memory"]
    )

    rag_score = sum(
        item["passed"]
        for item in results["vanilla_rag"]
    )

    results["summary"] = {
        "no_memory_score": no_memory_score,
        "vanilla_rag_score": rag_score,
        "total_cases": len(CASES),
    }

    output_dir = Path("benchmarks/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    output_path = (
        output_dir
        / f"p1-rag-smoke-{timestamp}.json"
    )

    output_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    print()
    print("===== SUMMARY =====")
    print(f"No Memory:  {no_memory_score}/5")
    print(f"Vanilla RAG: {rag_score}/5")
    print(f"RESULT_FILE: {output_path}")


if __name__ == "__main__":
    main()
