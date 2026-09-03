#!/usr/bin/env python3

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PROTOCOL_PATH = ROOT / "benchmarks/p3/p3-reviewer-critic-protocol-v0.1.json"
BLIND_PATH = ROOT / "benchmarks/p3/p3-benchmark-v0.1-blind-review.json"
OUTPUT_PATH = ROOT / "benchmarks/p3/p3-benchmark-v0.1-reviewer-critic-v0.1.json"

EXPECTED_PROTOCOL_SHA256 = (
    "ea3dbffb199e06847bec9f06df2cb8247fa1ffef3d95ec2e9a2ef80e164b6df3"
)

API_URL = "http://127.0.0.1:8095/v1/chat/completions"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text())


def build_schema(protocol):
    contract = protocol["output_contract"]
    families = protocol["relation_families"]

    return {
        "type": "object",
        "properties": {
            "blind_id": {
                "type": "string"
            },
            "candidate_assertion_ids": {
                "type": "array",
                "maxItems": contract["candidate_assertion_ids"]["max_items"],
                "items": {
                    "type": "string"
                }
            },
            "possible_relation_families": {
                "type": "array",
                "maxItems": contract["possible_relation_families"]["max_items"],
                "items": {
                    "type": "string",
                    "enum": families
                }
            },
            "strongest_objection": {
                "type": "string",
                "maxLength": contract["strongest_objection"]["max_length"]
            },
            "unresolved_alternatives": {
                "type": "array",
                "maxItems": contract["unresolved_alternatives"]["max_items"],
                "items": {
                    "type": "string",
                    "maxLength": contract["unresolved_alternatives"]["item_max_length"]
                }
            }
        },
        "required": [
            "blind_id",
            "candidate_assertion_ids",
            "possible_relation_families",
            "strongest_objection",
            "unresolved_alternatives"
        ],
        "additionalProperties": False
    }


def validate_protocol(protocol, protocol_sha):
    if protocol_sha != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            "Frozen protocol SHA256 mismatch.\n"
            f"Expected: {EXPECTED_PROTOCOL_SHA256}\n"
            f"Actual:   {protocol_sha}"
        )

    if protocol["protocol_id"] != "P3_REVIEWER_CRITIC_V0.1":
        raise RuntimeError("Unexpected protocol_id")

    if protocol["status"] != "FROZEN_FOR_BLIND_RUN":
        raise RuntimeError("Protocol is not frozen for blind run")

    if protocol["not_an_oracle"] is not True:
        raise RuntimeError("Protocol must declare not_an_oracle=true")

    if protocol["not_runtime_gate"] is not True:
        raise RuntimeError("Protocol must declare not_runtime_gate=true")


def validate_result(parsed, case, schema):
    if parsed["blind_id"] != case["blind_id"]:
        raise RuntimeError(
            f"{case['blind_id']}: reviewer returned wrong blind_id "
            f"{parsed['blind_id']!r}"
        )

    archive_ids = {
        a["assertion_id"]
        for a in case["archive_assertions"]
    }

    candidate_ids = parsed["candidate_assertion_ids"]

    if not set(candidate_ids) <= archive_ids:
        raise RuntimeError(
            f"{case['blind_id']}: reviewer returned unknown assertion ID"
        )

    if len(candidate_ids) > schema["properties"]["candidate_assertion_ids"]["maxItems"]:
        raise RuntimeError(f"{case['blind_id']}: too many candidate IDs")

    if len(parsed["possible_relation_families"]) > (
        schema["properties"]["possible_relation_families"]["maxItems"]
    ):
        raise RuntimeError(f"{case['blind_id']}: too many relation families")

    if len(parsed["strongest_objection"]) > (
        schema["properties"]["strongest_objection"]["maxLength"]
    ):
        raise RuntimeError(f"{case['blind_id']}: objection exceeds bound")

    alternatives = parsed["unresolved_alternatives"]

    if len(alternatives) > (
        schema["properties"]["unresolved_alternatives"]["maxItems"]
    ):
        raise RuntimeError(f"{case['blind_id']}: too many alternatives")

    item_limit = (
        schema["properties"]["unresolved_alternatives"]["items"]["maxLength"]
    )

    if any(len(x) > item_limit for x in alternatives):
        raise RuntimeError(f"{case['blind_id']}: alternative exceeds bound")


def make_payload(protocol, schema, case):
    model_cfg = protocol["model"]

    return {
        "model": model_cfg["alias"],
        "messages": [
            {
                "role": "system",
                "content": protocol["system_prompt"]
            },
            {
                "role": "user",
                "content": json.dumps(case, ensure_ascii=False)
            }
        ],
        "temperature": model_cfg["temperature"],
        "max_tokens": model_cfg["max_tokens"],
        "chat_template_kwargs": {
            "enable_thinking": model_cfg["thinking"]
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "p3_reviewer_critic_v0_1",
                "strict": True,
                "schema": schema
            }
        }
    }


def save_output(data):
    OUTPUT_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate frozen inputs without calling the model."
    )
    args = parser.parse_args()

    protocol_sha = sha256_file(PROTOCOL_PATH)
    blind_sha = sha256_file(BLIND_PATH)

    protocol = load_json(PROTOCOL_PATH)
    blind = load_json(BLIND_PATH)

    validate_protocol(protocol, protocol_sha)

    cases = blind["cases"]

    if len(cases) != 96:
        raise RuntimeError(f"Expected 96 blind cases, got {len(cases)}")

    blind_ids = [c["blind_id"] for c in cases]

    if len(set(blind_ids)) != 96:
        raise RuntimeError("Blind IDs are not unique")

    schema = build_schema(protocol)

    print("===== P3 REVIEWER CRITIC PREFLIGHT =====")
    print("PROTOCOL:", protocol["protocol_id"])
    print("STATUS:", protocol["status"])
    print("PROTOCOL SHA256:", protocol_sha)
    print("BLIND SHA256:", blind_sha)
    print("CASES:", len(cases))
    print("MODEL:", protocol["model"]["alias"])
    print("TEMPERATURE:", protocol["model"]["temperature"])
    print("THINKING:", protocol["model"]["thinking"])
    print("MAX TOKENS:", protocol["model"]["max_tokens"])
    print()
    print("SYSTEM PROMPT SOURCE:")
    print(PROTOCOL_PATH.relative_to(ROOT))
    print()
    print("OUTPUT FIELDS:")
    for field in schema["required"]:
        print(" -", field)

    if args.preflight:
        print()
        print("MODEL CALLS: 0")
        print("PREFLIGHT: PASS")
        return

    if OUTPUT_PATH.exists():
        output = load_json(OUTPUT_PATH)

        if output["protocol_sha256"] != protocol_sha:
            raise RuntimeError("Existing output uses a different protocol SHA")

        if output["blind_input_sha256"] != blind_sha:
            raise RuntimeError("Existing output uses a different blind input SHA")
    else:
        output = {
            "run_id": "P3_REVIEWER_CRITIC_V0.1_FIXED_BLIND_RUN",
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": protocol_sha,
            "blind_input_sha256": blind_sha,
            "model": protocol["model"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "results": []
        }
        save_output(output)

    completed = {
        r["blind_id"]
        for r in output["results"]
    }

    for index, case in enumerate(cases, start=1):
        blind_id = case["blind_id"]

        if blind_id in completed:
            print(f"[{index:02d}/96] {blind_id} SKIP (already saved)")
            continue

        payload = make_payload(protocol, schema, case)

        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

        start = time.perf_counter()

        with urllib.request.urlopen(req, timeout=120) as response:
            raw = json.loads(response.read().decode())

        elapsed = time.perf_counter() - start

        choice = raw["choices"][0]

        if choice.get("finish_reason") != "stop":
            raise RuntimeError(
                f"{blind_id}: finish_reason={choice.get('finish_reason')!r}"
            )

        content = choice["message"].get("content", "")
        parsed = json.loads(content)

        validate_result(parsed, case, schema)

        usage = raw.get("usage", {})

        record = {
            **parsed,
            "latency_seconds": round(elapsed, 3),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens")
        }

        output["results"].append(record)

        # Persist immediately after every successful case.
        save_output(output)

        print(
            f"[{index:02d}/96] {blind_id} OK"
            f" | candidates={len(parsed['candidate_assertion_ids'])}"
            f" | families={len(parsed['possible_relation_families'])}"
            f" | tokens={usage.get('completion_tokens')}",
            flush=True
        )

    output["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    save_output(output)

    print()
    print("FIXED BLIND RUN COMPLETE:", len(output["results"]))
    print("OUTPUT:", OUTPUT_PATH.relative_to(ROOT))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("RUN FAILED:", type(exc).__name__ + ":", exc, file=sys.stderr)
        sys.exit(1)
