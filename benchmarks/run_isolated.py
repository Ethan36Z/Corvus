#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DATA_DIR = (PROJECT_ROOT / "data").resolve()


def resolve_script(value: str) -> Path:
    path = Path(value)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise argparse.ArgumentTypeError(
            f"benchmark script does not exist: {path}"
        )

    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a Corvus benchmark in an isolated temporary "
            "memory environment."
        )
    )
    parser.add_argument(
        "script",
        type=resolve_script,
        help="Benchmark Python script to execute.",
    )
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the benchmark script.",
    )

    args = parser.parse_args()

    with tempfile.TemporaryDirectory(
        prefix="corvus-benchmark-"
    ) as temp_dir:
        data_dir = Path(temp_dir).resolve()

        if data_dir == PRODUCTION_DATA_DIR:
            raise RuntimeError(
                "Refusing to run benchmark against production data."
            )

        env = os.environ.copy()
        env["CORVUS_DATA_DIR"] = str(data_dir)
        env["CORVUS_BENCHMARK_ISOLATED"] = "1"

        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(PROJECT_ROOT)
            if not existing_pythonpath
            else str(PROJECT_ROOT)
            + os.pathsep
            + existing_pythonpath
        )

        command = [
            sys.executable,
            str(args.script),
            *args.script_args,
        ]

        print("===== CORVUS ISOLATED BENCHMARK =====")
        print("SCRIPT:", args.script)
        print("DATA_DIR:", data_dir)
        print()

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
        )

        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
