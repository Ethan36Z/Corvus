from memory.temporal_policy import (
    is_current_state_temporally_eligible,
)


def load_current_world_assertions(
    conn,
    *,
    support_checker,
    now=None,
):
    """
    Return assertions eligible for the CURRENT WORLD projection.

    Support is supplied by an external truth-maintenance layer.
    This function does not compute support itself.
    """

    rows = conn.execute(
        """
        SELECT
            id,
            subject,
            predicate,
            object,
            provenance,
            authority,
            modality,
            temporal_kind,
            time_start,
            time_end,
            temporal_granularity,
            recorded_at
        FROM assertions
        WHERE superseded_at IS NULL
          AND authority = 'ACCEPTED'
        ORDER BY id ASC
        """
    ).fetchall()

    result = []

    for row in rows:
        assertion_id = row[0]

        if not support_checker(assertion_id):
            continue

        if not is_current_state_temporally_eligible(
            modality=row[6],
            temporal_kind=row[7],
            time_start=row[8],
            time_end=row[9],
            now=now,
        ):
            continue

        result.append(row)

    return result
