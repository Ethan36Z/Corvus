from pathlib import Path
import sqlite3


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "corvus.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


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
