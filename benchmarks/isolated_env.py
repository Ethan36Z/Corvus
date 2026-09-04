import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DATA_DIR = (PROJECT_ROOT / "data").resolve()


def require_isolated_benchmark() -> Path:
    if os.environ.get("CORVUS_BENCHMARK_ISOLATED") != "1":
        raise RuntimeError(
            "Run memory benchmarks through "
            "benchmarks/run_isolated.py."
        )

    raw_data_dir = os.environ.get("CORVUS_DATA_DIR")
    if not raw_data_dir:
        raise RuntimeError(
            "CORVUS_DATA_DIR is required for memory benchmarks."
        )

    data_dir = Path(raw_data_dir).expanduser().resolve()

    if data_dir == PRODUCTION_DATA_DIR:
        raise RuntimeError(
            "Benchmark refuses to use production Corvus data."
        )

    return data_dir
