"""Provider-independent origin of context items (web source boundary).

Corvus decides where a memory item came from; a memory provider's labels are
never trusted. An item is ``user_said`` / ``assistant_said`` only if its id
resolves to a canonical Corvus message, and then the role AND content come
from the canonical SQLite row, not from the provider. Origin is identity, not
truth: ``user_said`` is personal context, never proof of an external fact.

Minimal provider contract: every item has ``content``. An item that is a
canonical Corvus message may carry that message's integer ``id`` (its role
and content are re-read from the canonical store). Anything summarized,
extracted or otherwise derived must use a non-integer, namespaced id (for
example ``hindsight:<id>``). Anything else fails safe as ``derived``.
"""
from contextlib import closing
from numbers import Integral
import sqlite3

USER_SAID = "user_said"
ASSISTANT_SAID = "assistant_said"
DERIVED = "derived"

# A web-grounded turn may use the user's own words as background. Prior model
# output, direct or derived, is never evidence for current external facts.
WEB_GROUNDED_HISTORY_ORIGINS = frozenset({USER_SAID})

_CANONICAL_ROLES = {"user": USER_SAID, "assistant": ASSISTANT_SAID}


def canonical_id(item):
    """The positive integer id an item claims, or None."""
    item_id = item.get("id") if isinstance(item, dict) else None
    if isinstance(item_id, Integral) and not isinstance(item_id, bool) and item_id > 0:
        return int(item_id)
    return None


def load_canonical_messages(message_ids):
    """Read-only lookup {id: {"role", "content"}} from the canonical store."""
    from memory import store  # resolved at call time (respects CORVUS_DATA_DIR)

    ids = sorted({int(i) for i in message_ids})
    if not ids:
        return {}
    path = store.DB_PATH.resolve()
    if not path.is_file():
        # Never create a store as a side effect of a lookup.
        raise sqlite3.OperationalError("canonical store is unavailable")
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA query_only = ON")
        rows = conn.execute(
            "SELECT id, role, content FROM messages WHERE id IN (%s)"
            % ",".join("?" * len(ids)),
            ids,
        ).fetchall()
    return {row[0]: {"role": row[1], "content": row[2]} for row in rows}


def resolve_origin(item, canonical_messages):
    """Return (origin, item_for_context) using only canonical data.

    A canonical item is returned with the canonical role and content; the
    provider's role/content are discarded. Everything else is ``derived``.
    """
    message_id = canonical_id(item)
    canonical = canonical_messages.get(message_id) if message_id else None
    if canonical is None or canonical["role"] not in _CANONICAL_ROLES:
        return DERIVED, item
    return _CANONICAL_ROLES[canonical["role"]], dict(
        item, role=canonical["role"], content=canonical["content"],
    )
