"""Dense bootstrap/incremental regressions against isolated real stores."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pyarrow as pa
import lancedb

from app.runtime_lifecycle import prepare_runtime_startup, recover_dense_tail
import memory.store as store
import memory.dense_index as dense

ROOT = Path(__file__).resolve().parents[1]


class FakeEmbeddingModel:
    def __init__(self):
        self.texts = []

    def encode(self, texts, **kwargs):
        self.texts.extend(texts)
        vectors = np.zeros((len(texts), dense.EMBEDDING_DIM), dtype=np.float32)
        vectors[:, 0] = 1
        return vectors


class DenseFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='.ow2e-test-', dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.db_path = self.directory / 'corvus.db'
        self.lance_path = self.directory / 'corvus-retrieval.lancedb'
        self.model = FakeEmbeddingModel()
        for patcher in (
            patch.object(store, 'DB_PATH', self.db_path),
            patch.object(dense, 'LANCE_DB_PATH', self.lance_path),
            patch.object(dense, 'load_embedding_model', return_value=self.model),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()

    def messages(self, count):
        with store.connect() as connection:
            for index in range(count):
                connection.execute(
                    'insert into messages(session_id,role,content,created_at) values(?,?,?,?)',
                    ('fixture', 'user', 'message ' + str(index + 1), '2026-10-03 00:00:00'),
                )

    def table(self):
        return lancedb.connect(str(self.lance_path)).open_table(dense.TABLE_NAME)

    def canonical(self):
        with store.connect() as connection:
            return connection.execute('select * from messages order by id').fetchall()

    def files(self):
        return {str(p.relative_to(self.lance_path)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.lance_path.rglob('*') if p.is_file()}


class DenseBootstrapTests(DenseFixture):
    def test_missing_table_zero_messages(self):
        result = prepare_runtime_startup()
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['progress_after'], 0)
        self.assertEqual(self.table().count_rows(), 0)
        self.assertTrue(self.table().schema.equals(dense.DENSE_SCHEMA, check_metadata=True))
        self.assertEqual(self.model.texts, [])

    def test_missing_table_existing_messages(self):
        self.messages(3)
        before = self.canonical()
        result = prepare_runtime_startup()
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['indexed'], 3)
        self.assertEqual(result['progress_after'], 3)
        self.assertEqual(self.table().count_rows(), 3)
        self.assertEqual(dense.classify_dense_message_ids([1, 2, 3])['current'], [1, 2, 3])
        self.assertEqual(self.canonical(), before)
        self.assertEqual(self.model.texts, ['message 1', 'message 2', 'message 3'])

    def test_existing_current_rows_are_not_reembedded_or_replaced(self):
        self.messages(2)
        dense.sync_dense_message_ids([1, 2])
        before, version = self.files(), self.table().version
        self.model.texts.clear()
        result = prepare_runtime_startup()
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['indexed'], 0)
        self.assertEqual(result['progress_after'], 2)
        self.assertEqual(self.model.texts, [])
        self.assertEqual(self.table().version, version)
        self.assertEqual(self.files(), before)

    def test_second_startup_is_idempotent(self):
        self.messages(2)
        prepare_runtime_startup()
        before, version = self.files(), self.table().version
        self.model.texts.clear()
        result = prepare_runtime_startup()
        self.assertEqual(result['indexed'], 0)
        self.assertEqual(result['batches'], 0)
        self.assertEqual(result['progress_after'], 2)
        self.assertEqual(self.model.texts, [])
        self.assertEqual(self.table().version, version)
        self.assertEqual(self.files(), before)

    def test_partial_progress_resumes_without_reembedding_prefix(self):
        self.messages(3)
        first = recover_dense_tail(batch_size=1, max_batches=1)
        self.assertEqual(first['status'], 'BOUNDED')
        self.assertEqual(dense.get_dense_progress(), 1)
        self.assertEqual(self.table().count_rows(), 1)
        self.model.texts.clear()
        second = recover_dense_tail(batch_size=1, max_batches=8)
        self.assertEqual(second['status'], 'OK')
        self.assertEqual(second['indexed'], 2)
        self.assertEqual(second['progress_after'], 3)
        self.assertEqual(self.model.texts, ['message 2', 'message 3'])
        self.assertEqual(self.table().count_rows(), 3)

    def test_failed_sync_does_not_advance_progress(self):
        self.messages(2)
        before = self.canonical()
        with patch.object(self.model, 'encode', side_effect=RuntimeError('synthetic failure')):
            result = prepare_runtime_startup()
        self.assertEqual(result['status'], 'DEGRADED')
        self.assertEqual(dense.get_dense_progress(), 0)
        self.assertEqual(self.table().count_rows(), 0)
        self.assertEqual(self.canonical(), before)
        recovered = prepare_runtime_startup()
        self.assertEqual(recovered['status'], 'OK')
        self.assertEqual(recovered['progress_after'], 2)

    def test_stale_row_is_incrementally_repaired_without_rebuild(self):
        self.messages(2)
        dense.sync_dense_message_ids([1, 2])
        table = self.table()
        table.update(where='message_id = 2', values={'content_sha256': 'stale'})
        self.model.texts.clear()
        result = dense.sync_dense_message_ids([1, 2])
        self.assertEqual(result['indexed'], 1)
        self.assertEqual(result['current'], [1])
        self.assertEqual(self.model.texts, ['message 2'])
        self.assertEqual(self.table().count_rows(), 2)
        self.assertEqual(dense.classify_dense_message_ids([1, 2])['current'], [1, 2])

    def test_incompatible_existing_schema_fails_without_overwrite(self):
        db = lancedb.connect(str(self.lance_path))
        table = db.create_table(dense.TABLE_NAME, schema=pa.schema([pa.field('sentinel', pa.string())]))
        table.add([{'sentinel': 'preserve'}])
        before = self.files()
        with self.assertRaises(ValueError):
            dense.ensure_dense_table()
        self.assertEqual(db.open_table(dense.TABLE_NAME).to_arrow().to_pylist(),
                         [{'sentinel': 'preserve'}])
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
