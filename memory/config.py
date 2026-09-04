import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

_data_dir_env = os.environ.get("CORVUS_DATA_DIR")

DATA_DIR = (
    Path(_data_dir_env).expanduser()
    if _data_dir_env
    else PROJECT_ROOT / "data"
).resolve()

DB_PATH = DATA_DIR / "corvus.db"
LANCE_DB_PATH = DATA_DIR / "corvus-retrieval.lancedb"
