import sqlite3

from memory.config import DB_PATH




def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assertions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,

                provenance TEXT NOT NULL,
                authority TEXT NOT NULL,
                modality TEXT,

                temporal_kind TEXT NOT NULL DEFAULT 'UNKNOWN',
                time_start TEXT,
                time_end TEXT,
                temporal_granularity TEXT,

                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                superseded_at TEXT,
                superseded_by_assertion_id INTEGER,

                FOREIGN KEY (superseded_by_assertion_id)
                    REFERENCES assertions(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assertion_message_basis (
                assertion_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                PRIMARY KEY (assertion_id, message_id),

                FOREIGN KEY (assertion_id)
                    REFERENCES assertions(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (message_id)
                    REFERENCES messages(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assertion_assertion_basis (
                assertion_id INTEGER NOT NULL,
                basis_assertion_id INTEGER NOT NULL,

                PRIMARY KEY (assertion_id, basis_assertion_id),

                CHECK (assertion_id != basis_assertion_id),

                FOREIGN KEY (assertion_id)
                    REFERENCES assertions(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (basis_assertion_id)
                    REFERENCES assertions(id)
            )
            """
        )

        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(
                content,
                content='messages',
                content_rowid='id'
            )
            """
        )

        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_ai
            AFTER INSERT ON messages
            BEGIN
                INSERT INTO messages_fts(rowid, content)
                VALUES (new.id, new.content);
            END
            """
        )

        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_ad
            AFTER DELETE ON messages
            BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
            END
            """
        )

        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_au
            AFTER UPDATE ON messages
            BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);

                INSERT INTO messages_fts(rowid, content)
                VALUES (new.id, new.content);
            END
            """
        )

        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Corvus memory store ready: {DB_PATH}")


def add_message(session_id, role, content):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )
        conn.commit()
        return cursor.lastrowid


def load_session(session_id):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return [
        {"role": role, "content": content}
        for role, content in rows
    ]



def load_recent_messages(
    session_id,
    limit=64,
    before_message_id=None,
):
    """
    Load a bounded tail of canonical messages for one session.

    Results are returned in chronological order for direct use when
    constructing Recent Conversation Context.

    If before_message_id is provided, only messages with smaller canonical
    IDs are eligible. This lets the runtime commit the current user message
    first while reconstructing only the prior conversation context.
    """
    limit = int(limit)

    if limit <= 0:
        raise ValueError(
            "limit must be positive"
        )

    clauses = [
        "session_id = ?",
    ]
    params = [
        str(session_id),
    ]

    if before_message_id is not None:
        before_message_id = int(
            before_message_id
        )

        if before_message_id <= 0:
            raise ValueError(
                "before_message_id must be positive"
            )

        clauses.append(
            "id < ?"
        )
        params.append(
            before_message_id
        )

    params.append(
        limit
    )

    where_clause = " AND ".join(
        clauses
    )

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                id,
                session_id,
                role,
                content,
                created_at
            FROM messages
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    rows.reverse()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

def search_messages(query, limit=5):
    pattern = f"%{query}%"

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE content LIKE ? COLLATE NOCASE
            ORDER BY id DESC
            LIMIT ?
            """,
            (pattern, limit),
        ).fetchall()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]
