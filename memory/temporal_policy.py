from datetime import datetime, timezone


def _parse_time(value):
    if value is None:
        return None

    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        raise ValueError(
            "Temporal policy requires timezone-aware timestamps"
        )

    return dt


def is_current_state_temporally_eligible(
    *,
    modality,
    temporal_kind,
    time_start=None,
    time_end=None,
    now=None,
):
    """
    Return whether an assertion is temporally eligible
    for the CURRENT STATE projection.

    This function does NOT decide:
    - authority
    - support
    - supersession
    - provenance

    Those belong to other layers.
    """

    if modality != "ASSERTED":
        return False

    if temporal_kind != "STATE_VALIDITY":
        return False

    current = now or datetime.now(timezone.utc)

    if current.tzinfo is None:
        raise ValueError(
            "now must be timezone-aware"
        )

    start = _parse_time(time_start)
    end = _parse_time(time_end)

    # Half-open validity interval: [start, end)
    if start is not None and current < start:
        return False

    if end is not None and current >= end:
        return False

    return True
