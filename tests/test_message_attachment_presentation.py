import os
import tempfile


DATA = tempfile.TemporaryDirectory()
os.environ["CORVUS_DATA_DIR"] = DATA.name

from memory.store import (
    add_message,
    init_db,
)
from memory.attachments import (
    link_attachment_to_message,
    store_attachment_bytes,
)
from app.playground_api import (
    get_attachment_content,
    load_message_attachments,
    public_attachment_metadata,
)


init_db()

attachment = store_attachment_bytes(
    b"\x89PNG\r\n\x1a\nfake-test-payload",
    original_filename="photo.png",
    media_type="image/png",
    retention_class="STANDARD",
)

message_id = add_message(
    "presentation-test",
    "user",
    "What is in this image?",
)

link_attachment_to_message(
    message_id,
    attachment["id"],
    ordinal=0,
)

mapping = load_message_attachments(
    [message_id]
)

assert message_id in mapping
assert len(mapping[message_id]) == 1

shown = mapping[message_id][0]

assert shown["id"] == attachment["id"]
assert shown["ordinal"] == 0
assert shown["original_filename"] == "photo.png"
assert shown["media_type"] == "image/png"
assert shown["blob_status"] == "PRESENT"

assert shown["content_url"] == (
    f"/api/attachments/"
    f"{attachment['id']}/content"
)

assert "storage_path" not in shown
assert "sha256" not in shown

public = public_attachment_metadata(
    attachment
)

assert public["id"] == attachment["id"]

assert public["content_url"] == (
    f"/api/attachments/"
    f"{attachment['id']}/content"
)

assert "storage_path" not in public
assert "sha256" not in public

response = get_attachment_content(
    attachment["id"]
)

assert response.status_code == 200
assert response.body == (
    b"\x89PNG\r\n\x1a\nfake-test-payload"
)

assert (
    response.media_type
    == "image/png"
)

assert (
    response.headers[
        "x-content-type-options"
    ]
    == "nosniff"
)

print(
    "MESSAGE ATTACHMENT METADATA CONTRACT OK"
)

print(
    "ATTACHMENT STORAGE PATH PRIVACY CONTRACT OK"
)

print(
    "ATTACHMENT CONTENT READ CONTRACT OK"
)

print(
    "A3 MESSAGE ATTACHMENT PRESENTATION: PASS"
)

DATA.cleanup()
