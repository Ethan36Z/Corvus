"""Provider-independent origin of context items (web source boundary).

Corvus decides where a memory item came from; a memory provider's own label
is never trusted. Origin is identity, not truth: ``user_said`` is personal
context, never proof of an external fact.

Minimal provider contract: every item has ``content``. Only items that are a
canonical Corvus message may carry its canonical integer ``id`` and real
``role``. Anything summarized, extracted or otherwise derived must use a
non-integer, namespaced id (for example ``hindsight:<id>``); its role is
ignored. Items that break the contract fail safe: they become ``derived``.
"""
from numbers import Integral

USER_SAID = "user_said"
ASSISTANT_SAID = "assistant_said"
DERIVED = "derived"

# A web-grounded turn may use the user's own words as background. Prior model
# output, direct or derived, is never evidence for current external facts.
WEB_GROUNDED_HISTORY_ORIGINS = frozenset({USER_SAID})


def memory_origin(item):
    item_id = item.get("id") if isinstance(item, dict) else None
    canonical = (
        isinstance(item_id, Integral)
        and not isinstance(item_id, bool)
        and item_id > 0
    )
    if canonical and item.get("role") == "user":
        return USER_SAID
    if canonical and item.get("role") == "assistant":
        return ASSISTANT_SAID
    return DERIVED
