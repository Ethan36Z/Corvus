def would_create_cycle(conn, assertion_id, basis_assertion_id):
    """
    Return True if adding:

        assertion_id -> basis_assertion_id

    would create a cycle in the assertion justification graph.
    """

    if assertion_id == basis_assertion_id:
        return True

    row = conn.execute(
        """
        WITH RECURSIVE ancestors(id) AS (
            SELECT basis_assertion_id
            FROM assertion_assertion_basis
            WHERE assertion_id = ?

            UNION

            SELECT aab.basis_assertion_id
            FROM assertion_assertion_basis aab
            JOIN ancestors a
              ON aab.assertion_id = a.id
        )
        SELECT 1
        FROM ancestors
        WHERE id = ?
        LIMIT 1
        """,
        (
            basis_assertion_id,
            assertion_id,
        ),
    ).fetchone()

    return row is not None


def add_assertion_basis(conn, assertion_id, basis_assertion_id):
    if would_create_cycle(
        conn,
        assertion_id=assertion_id,
        basis_assertion_id=basis_assertion_id,
    ):
        raise ValueError(
            f"Assertion dependency cycle rejected: "
            f"{assertion_id} -> {basis_assertion_id}"
        )

    conn.execute(
        """
        INSERT INTO assertion_assertion_basis (
            assertion_id,
            basis_assertion_id
        )
        VALUES (?, ?)
        """,
        (
            assertion_id,
            basis_assertion_id,
        ),
    )


def add_assertion(
    conn,
    *,
    subject,
    predicate,
    object_,
    provenance,
    authority,
    modality=None,
    temporal_kind="UNKNOWN",
    time_start=None,
    time_end=None,
    temporal_granularity=None,
):
    cursor = conn.execute(
        """
        INSERT INTO assertions (
            subject,
            predicate,
            object,
            provenance,
            authority,
            modality,
            temporal_kind,
            time_start,
            time_end,
            temporal_granularity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subject,
            predicate,
            object_,
            provenance,
            authority,
            modality,
            temporal_kind,
            time_start,
            time_end,
            temporal_granularity,
        ),
    )

    return cursor.lastrowid


def add_message_basis(conn, assertion_id, message_id):
    conn.execute(
        """
        INSERT INTO assertion_message_basis (
            assertion_id,
            message_id
        )
        VALUES (?, ?)
        """,
        (
            assertion_id,
            message_id,
        ),
    )


def supersede_assertion(conn, old_assertion_id, new_assertion_id):
    if old_assertion_id == new_assertion_id:
        raise ValueError("An assertion cannot supersede itself")

    new_row = conn.execute(
        """
        SELECT id
        FROM assertions
        WHERE id = ?
        """,
        (new_assertion_id,),
    ).fetchone()

    if new_row is None:
        raise ValueError(
            f"New assertion does not exist: {new_assertion_id}"
        )

    old_row = conn.execute(
        """
        SELECT superseded_at, superseded_by_assertion_id
        FROM assertions
        WHERE id = ?
        """,
        (old_assertion_id,),
    ).fetchone()

    if old_row is None:
        raise ValueError(
            f"Old assertion does not exist: {old_assertion_id}"
        )

    if old_row[0] is not None:
        raise ValueError(
            f"Assertion {old_assertion_id} is already superseded"
        )

    conn.execute(
        """
        UPDATE assertions
        SET
            superseded_at = CURRENT_TIMESTAMP,
            superseded_by_assertion_id = ?
        WHERE id = ?
        """,
        (
            new_assertion_id,
            old_assertion_id,
        ),
    )


def load_unsuperseded_assertions(conn):
    """
    Return the latest unsuperseded assertion versions.

    Note:
    unsuperseded does NOT necessarily mean currently true or realized.
    World-state projection is a separate concern.
    """

    return conn.execute(
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
        ORDER BY id ASC
        """
    ).fetchall()
