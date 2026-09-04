from fastapi import FastAPI

from memory.store import connect

app = FastAPI(title="Corvus Playground API")


@app.get("/api/evidence")
def get_evidence():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT 100
            """
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

from memory.assertion_store import load_unsuperseded_assertions


@app.get("/api/assertions")
def get_assertions():
    with connect() as conn:
        rows = load_unsuperseded_assertions(conn)

    return [
        {
            "id": row[0],
            "subject": row[1],
            "predicate": row[2],
            "object": row[3],
            "provenance": row[4],
            "authority": row[5],
            "modality": row[6],
            "temporal_kind": row[7],
            "time_start": row[8],
            "time_end": row[9],
            "temporal_granularity": row[10],
            "recorded_at": row[11],
        }
        for row in rows
    ]
