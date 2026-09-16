from app.runtime_config import (
    RECOVERY_BATCH_SIZE,
    RECOVERY_MAX_BATCHES,
)
from memory.dense_index import sync_dense_tail_once
from memory.store import init_db


def recover_dense_tail(
    batch_size=RECOVERY_BATCH_SIZE,
    max_batches=RECOVERY_MAX_BATCHES,
    sync_fn=sync_dense_tail_once,
):
    """
    Run bounded startup recovery for derived dense state.
    """
    batches = 0
    indexed = 0
    progress_after = None

    try:
        for _ in range(max_batches):
            result = sync_fn(
                limit=batch_size
            )

            progress_after = result[
                "progress_after"
            ]

            if not result["message_ids"]:
                return {
                    "status": "OK",
                    "caught_up": True,
                    "batches": batches,
                    "indexed": indexed,
                    "progress_after": progress_after,
                    "error": None,
                }

            batches += 1
            indexed += result["indexed"]

    except Exception as exc:
        return {
            "status": "DEGRADED",
            "caught_up": False,
            "batches": batches,
            "indexed": indexed,
            "progress_after": progress_after,
            "error": str(exc),
        }

    return {
        "status": "BOUNDED",
        "caught_up": False,
        "batches": batches,
        "indexed": indexed,
        "progress_after": progress_after,
        "error": None,
    }



def prepare_runtime_startup(
    schema_ensure_fn=init_db,
    recovery_fn=recover_dense_tail,
):
    """
    Prepare canonical and derived runtime state.

    Canonical SQLite schema must be ensured before
    any derived dense recovery runs.

    Schema failure is fatal to startup. Dense recovery
    retains its existing degraded / bounded semantics.
    """

    schema_ensure_fn()

    return recovery_fn()
