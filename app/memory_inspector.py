from memory.store import connect

ABSOLUTE_SESSION_ID = "p2a-s2a-demo"
RELATIVE_SESSION_ID = "p2a-relative-demo"

with connect() as conn:
    absolute_rows = conn.execute(
        """
        SELECT
            m.id,
            m.content,
            m.created_at,
            i.memory_kind,
            i.modality,
            i.event_time,
            i.temporal_source,
            i.provenance,
            i.created_at
        FROM messages m
        LEFT JOIN memory_interpretations i
          ON i.message_id = m.id
        WHERE m.session_id = ?
        ORDER BY m.id ASC
        """,
        (ABSOLUTE_SESSION_ID,),
    ).fetchall()

    relative_rows = conn.execute(
        """
        SELECT
            r.id,
            sm.id,
            sm.content,
            r.relation,
            tm.id,
            tm.content,
            r.provenance
        FROM temporal_relations r
        JOIN messages sm
          ON sm.id = r.source_message_id
        JOIN messages tm
          ON tm.id = r.target_message_id
        WHERE sm.session_id = ?
        ORDER BY r.id ASC
        """,
        (RELATIVE_SESSION_ID,),
    ).fetchall()

print("===== CORVUS MEMORY INSPECTOR — S2A =====")
print()

print("===== ABSOLUTE TEMPORAL ANCHORS =====")
print()

interpreted_rows = []

for row in absolute_rows:
    (
        message_id,
        content,
        recorded_at,
        memory_kind,
        modality,
        event_time,
        temporal_source,
        provenance,
        interpretation_created_at,
    ) = row

    print(f"MEMORY #{message_id}")
    print(f"RAW EVIDENCE       : {content}")
    print(f"RECORDED AT        : {recorded_at}")
    print(f"MEMORY KIND        : {memory_kind or 'UNINTERPRETED'}")
    print(f"MODALITY           : {modality or 'UNINTERPRETED'}")
    print(f"ABSOLUTE TIME      : {event_time or 'UNKNOWN'}")
    print(f"TEMPORAL SOURCE    : {temporal_source or 'UNKNOWN'}")
    print(f"PROVENANCE         : {provenance or 'UNINTERPRETED'}")
    print(f"INTERPRETED AT     : {interpretation_created_at or 'N/A'}")
    print("-" * 60)

    if memory_kind and event_time:
        interpreted_rows.append({
            "id": message_id,
            "content": content,
            "event_time": event_time,
            "provenance": provenance,
        })

print()
print("===== RELATIVE TEMPORAL RELATIONS =====")
print()

if relative_rows:
    for (
        relation_id,
        source_id,
        source_content,
        relation,
        target_id,
        target_content,
        provenance,
    ) in relative_rows:
        print(f"RELATION #{relation_id}")
        print(f"SOURCE MEMORY      : #{source_id} — {source_content}")
        print(f"RELATION           : {relation}")
        print(f"TARGET MEMORY      : #{target_id} — {target_content}")
        print(f"PROVENANCE         : {provenance}")
        print("-" * 60)
else:
    print("No relative temporal relations found.")

print()
print("===== DERIVED TEMPORAL PROJECTION — DEMO ONLY =====")
print()

if interpreted_rows:
    latest = sorted(
        interpreted_rows,
        key=lambda item: item["event_time"],
        reverse=True,
    )[0]

    print("This is a temporary S2A projection, not stored memory truth.")
    print(f"CANDIDATE MEMORY   : #{latest['id']}")
    print(f"CONTENT            : {latest['content']}")
    print(f"ABSOLUTE TIME      : {latest['event_time']}")
    print("DERIVATION         : DERIVED_DETERMINISTIC")
    print("RULE               : latest known absolute-time state candidate")
else:
    print("No interpreted temporal memories found.")
