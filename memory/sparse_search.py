import re

from memory.store import connect


def prepare_fts_query(query):
    stopwords = {
        "a", "an", "the",
        "what", "where", "when", "who", "why", "how",
        "is", "are", "was", "were",
        "do", "does", "did",
        "my", "your", "i", "you",
        "for", "to", "of", "in", "on",
        "use", "uses",
    }

    terms = [
        term
        for term in re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        if term not in stopwords
    ]

    if not terms:
        return None

    return " OR ".join(f'"{term}"' for term in terms)


def sparse_search(
    query,
    limit=5,
    session_id=None,
    role=None,
):
    fts_query = prepare_fts_query(query)

    if not fts_query:
        return []

    clauses = [
        "messages_fts MATCH ?",
    ]
    params = [
        fts_query,
    ]

    if session_id is not None:
        clauses.append(
            "messages.session_id = ?"
        )
        params.append(
            str(session_id)
        )

    if role is not None:
        clauses.append(
            "messages.role = ?"
        )
        params.append(
            str(role)
        )

    params.append(
        int(limit)
    )

    where_clause = " AND ".join(
        clauses
    )

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                messages.id,
                messages.session_id,
                messages.role,
                messages.content,
                messages.created_at,
                bm25(messages_fts) AS score
            FROM messages_fts
            JOIN messages
                ON messages.id = messages_fts.rowid
            WHERE {where_clause}
            ORDER BY score ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
            "score": row[5],
        }
        for row in rows
    ]


if __name__ == "__main__":
    query = "What port does Project Lantern use?"

    print("QUERY:", query)
    print()

    for rank, item in enumerate(
        sparse_search(query, limit=5),
        start=1,
    ):
        print(
            rank,
            f'{item["score"]:.6f}',
            f'#{item["id"]}',
            item["role"],
            item["content"],
        )
