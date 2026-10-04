"""Read-only dense readiness, independent of cached API startup health."""
import json
import os
from pathlib import Path
import sqlite3
import sys

LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB))

from memory.config import DB_PATH, LANCE_DB_PATH
from memory.dense_index import (
    DENSE_SCHEMA, EMBEDDING_DIM, INDEX_SCHEMA_VERSION,
    MODEL_NAME, MODEL_REVISION, TABLE_NAME, content_sha256,
)
import lancedb


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_dense_state(db_path=DB_PATH, lance_path=LANCE_DB_PATH):
    db_path, lance_path = Path(db_path), Path(lance_path)
    require(lance_path.is_dir(), 'Dense directory is missing')
    require(not any(Path(str(db_path) + suffix).exists()
                    for suffix in ('-wal', '-shm', '-journal')),
            'Review SQLite sidecars before immutable dense readiness read')
    fd = os.open(db_path, os.O_RDONLY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        with sqlite3.connect('file:/proc/self/fd/' + str(fd) + '?mode=ro&immutable=1',
                             uri=True) as connection:
            connection.execute('pragma query_only=ON')
            source = connection.execute(
                'select id,session_id,role,content,created_at from messages order by id'
            ).fetchall()
            progress_row = connection.execute(
                'select last_message_id from dense_index_progress where index_name=?',
                (TABLE_NAME,),
            ).fetchone()
        progress = 0 if progress_row is None else progress_row[0]
        table = lancedb.connect(str(lance_path)).open_table(TABLE_NAME)
        require(table.schema.equals(DENSE_SCHEMA, check_metadata=True),
                'Dense schema differs from the pinned contract')
        indexed = table.search().select([
            'message_id', 'session_id', 'role', 'created_at', 'content_sha256',
            'embedding_model', 'embedding_revision', 'embedding_dim', 'schema_version',
        ]).to_list()
        indexed_by_id = {row['message_id']: row for row in indexed}
        require(len(indexed_by_id) == len(indexed), 'Duplicate dense message IDs')
        require(set(indexed_by_id) == {row[0] for row in source},
                'Dense rows do not exactly cover canonical messages')
        for message_id, session_id, role, content, created_at in source:
            require(indexed_by_id[message_id] == {
                'message_id': message_id, 'session_id': session_id, 'role': role,
                'created_at': created_at, 'content_sha256': content_sha256(content),
                'embedding_model': MODEL_NAME, 'embedding_revision': MODEL_REVISION,
                'embedding_dim': EMBEDDING_DIM, 'schema_version': INDEX_SCHEMA_VERSION,
            }, 'Dense metadata differs for canonical message ' + str(message_id))
        maximum = max((row[0] for row in source), default=0)
        require(progress == maximum, 'Dense progress is not caught up to canonical messages')
        after = os.fstat(fd)
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
                and not any(Path(str(db_path) + suffix).exists()
                            for suffix in ('-wal', '-shm', '-journal')),
                'Canonical database changed during dense readiness read')
        return {'table': TABLE_NAME, 'canonical_messages': len(source),
                'indexed_messages': len(indexed), 'progress_after': progress,
                'caught_up': True}
    finally:
        os.close(fd)


if __name__ == '__main__':
    print(json.dumps(verify_dense_state(), sort_keys=True))
