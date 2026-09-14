import importlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix="corvus-a3-stt-contract-"
    )
)

try:
    os.environ[
        "CORVUS_DATA_DIR"
    ] = str(tmp_root)

    os.environ[
        "CORVUS_STT_BASE_URL"
    ] = "http://127.0.0.1:8104"

    os.environ[
        "CORVUS_STT_PROMPT"
    ] = (
        "Corvus Ethan FoxLuma "
        "FoxRove PawCareHub"
    )

    import memory.config
    import memory.store
    import memory.attachments
    import app.transcription

    importlib.reload(
        memory.config
    )
    importlib.reload(
        memory.store
    )
    importlib.reload(
        memory.attachments
    )
    importlib.reload(
        app.transcription
    )

    config = memory.config
    store = memory.store
    attachments = (
        memory.attachments
    )
    transcription = (
        app.transcription
    )

    store.init_db()

    audio_payload = (
        b"fake-m4a-audio-bytes"
    )

    attachment = (
        attachments.store_attachment_stream(
            io.BytesIO(
                audio_payload
            ),
            original_filename=(
                "corvus-test.m4a"
            ),
            media_type="audio/mp4",
            retention_class="STANDARD",
            max_bytes=1024,
        )
    )

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def read(self):
            return json.dumps({
                "text": (
                    "我们今天测试 Corvus "
                    "的语音功能."
                ),
            }).encode("utf-8")

    def fake_opener(
        request,
        timeout,
    ):
        captured[
            "url"
        ] = request.full_url

        captured[
            "timeout"
        ] = timeout

        captured[
            "content_type"
        ] = request.headers.get(
            "Content-type"
        )

        captured[
            "body"
        ] = request.data

        return FakeResponse()

    result = (
        transcription
        .transcribe_attachment(
            attachment["id"],
            opener=fake_opener,
        )
    )

    assert result[
        "attachment_id"
    ] == attachment["id"]

    assert result[
        "transcript"
    ] == (
        "我们今天测试 Corvus "
        "的语音功能."
    )

    assert (
        captured["url"]
        == (
            "http://127.0.0.1:8104"
            "/inference"
        )
    )

    assert (
        captured["timeout"]
        == 60
    )

    assert (
        "multipart/form-data"
        in captured[
            "content_type"
        ]
    )

    body = captured[
        "body"
    ]

    assert (
        b'name="file"'
        in body
    )

    assert (
        b'filename="corvus-test.m4a"'
        in body
    )

    assert (
        b"Content-Type: audio/mp4"
        in body
    )

    assert (
        audio_payload
        in body
    )

    assert (
        b'name="language"'
        in body
    )

    assert (
        b"Corvus Ethan FoxLuma"
        in body
    )

    with sqlite3.connect(
        config.DB_PATH
    ) as conn:
        artifact = conn.execute(
            """
            SELECT
                attachment_id,
                artifact_kind,
                content,
                producer,
                producer_version
            FROM attachment_artifacts
            WHERE id = ?
            """,
            (
                result[
                    "artifact_id"
                ],
            ),
        ).fetchone()

    assert artifact == (
        attachment["id"],
        "TRANSCRIPT",
        (
            "我们今天测试 Corvus "
            "的语音功能."
        ),
        "whisper.cpp",
        "small-multilingual",
    )

    text_attachment = (
        attachments
        .store_attachment_bytes(
            b"not audio",
            original_filename="note.txt",
            media_type="text/plain",
            max_bytes=1024,
        )
    )

    try:
        transcription.transcribe_attachment(
            text_attachment["id"],
            opener=fake_opener,
        )
    except (
        transcription.TranscriptionError
    ) as exc:
        assert (
            exc.code
            == "TRANSCRIPTION_MEDIA_INVALID"
        )
    else:
        raise AssertionError(
            "non-audio attachment "
            "was accepted by STT"
        )

    print(
        "TRANSCRIPTION ADAPTER CONTRACT OK"
    )
    print(
        "TRANSCRIPT ARTIFACT PROVENANCE OK"
    )
    print(
        "NON-AUDIO REJECTION OK"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
