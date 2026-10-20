"""Lab-only Corvus reference adapter. File rows hold metadata, never image bytes.

Installed by prepare_vision.py into the pinned WebUI process. No new service,
engine or persistent store. Disabled unless explicitly enabled in a later run.
"""
import asyncio
import hashlib
import json
import os
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from open_webui.internal.db import get_db
from open_webui.models.files import File
from open_webui.models.chats import Chat
from open_webui.models.functions import Functions
from open_webui.utils.auth import get_verified_user

PROVIDER = "corvus-vision-v1"
LIMIT = 6 * 1024 * 1024
BASE = "http://127.0.0.1:18096"
router = APIRouter()


def enabled():
    if os.getenv("CORVUS_SINGLE_STORE_VISION") != "offline-reviewed-v1":
        raise HTTPException(404, "Image integration is disabled")


def uid(value):
    try:
        if str(UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise HTTPException(400, "Invalid image binding")


def namespace():
    valves = Functions.get_function_valves_by_id("corvus_pipe") or {}
    if valves.get("CORVUS_CHAT_URL") != BASE + "/api/chat" or not valves.get("INSTANCE_ID"):
        raise HTTPException(503, "Image integration is unavailable")
    return valves["INSTANCE_ID"]


def owned(db, user_id, chat_id, message_id):
    chat = db.get(Chat, uid(chat_id))
    message = ((chat.chat or {}).get("history", {}).get("messages", {}).get(message_id)
               if chat and chat.user_id == user_id and chat.share_id is None else None)
    if not isinstance(message, dict) or message.get("id") != uid(message_id) or message.get("role") != "user":
        raise HTTPException(404, "Image binding is unavailable")
    return chat, message


def ref(file):
    return {"type": "image", "corvus_ref": file.id,
            "url": "/api/v1/files/" + file.id + "/content"}


def is_reference(file):
    return file is not None and (file.meta or {}).get("provider") == PROVIDER


def authority(db, file, user_id, *, membership=True):
    if not is_reference(file) or file.user_id != user_id or file.path is not None or file.data != {}:
        raise HTTPException(404, "Image binding is unavailable")
    meta = file.meta
    allowed = {"READY", "CLAIMED", "COMMITTED", "UNCERTAIN"} if membership else {"READY", "CLAIMED", "COMMITTED", "UNCERTAIN", "REVOKED"}
    if meta.get("instance") != namespace() or meta.get("state") not in allowed:
        raise HTTPException(404, "Image binding is unavailable")
    chat, message = owned(db, user_id, meta["chat_id"], meta["message_id"])
    if membership and message.get("files") != [ref(file)]:
        raise HTTPException(404, "Image binding is unavailable")
    return chat, message


def reject_bytes(value):
    """Called at every native chat write, including import and share/clone."""
    if isinstance(value, str):
        if "data:image/" in value.lower() or value.lower().startswith("blob:"):
            raise ValueError("Transient image data cannot be saved")
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"images", "image_url", "attachment_id"} and item:
                raise ValueError("Unsupported image serialization")
            reject_bytes(item)
    elif isinstance(value, list):
        for item in value:
            reject_bytes(item)


def references(value):
    if isinstance(value, dict):
        if value.get("type") == "image" or "corvus_ref" in value:
            return [value]
        return [item for child in value.values() for item in references(child)]
    if isinstance(value, list):
        return [item for child in value for item in references(child)]
    return []


def validate_chat(db, user_id, chat_id, value, *, transfer=False):
    reject_bytes(value)
    body = value.get("chat", value)
    messages = body.get("history", {}).get("messages", {})
    for message in messages.values():
        if message.get("corvus_image_pending") or references(message):
            if (message.get("models") != ["corvus_pipe"]
                    or any(messages.get(child, {}).get("model") != "corvus_pipe"
                           for child in message.get("childrenIds", []))):
                raise ValueError("Image turns require the Corvus Pipe")
            if any(messages.get(child, {}).get("corvus_arena_requested") for child in message.get("childrenIds", [])):
                raise ValueError("Images cannot be combined with Arena")
    found = references(value)
    if not found:
        return
    enabled()
    if transfer or not chat_id:
        raise ValueError("Image imports, clones and sharing are unsupported")
    chat = db.get(Chat, chat_id)
    if not chat or chat.user_id != user_id or chat.share_id:
        raise ValueError("Invalid image owner")
    messages = value.get("history", {}).get("messages", {})
    expected = []
    for message_id, message in messages.items():
        images = references(message)
        if not images:
            continue
        if message.get("id") != message_id or message.get("role") != "user" or len(images) != 1:
            raise ValueError("Invalid image message")
        file = db.get(File, images[0].get("corvus_ref"))
        authority(db, file, user_id, membership=False)
        if file.meta["chat_id"] != chat_id or file.meta["message_id"] != message_id or message.get("files") != [ref(file)]:
            raise ValueError("Invalid image reference")
        if file.meta["state"] in {"CLAIMED", "UNCERTAIN", "COMMITTED"}:
            previous = chat.chat.get("history", {}).get("messages", {}).get(message_id, {})
            if previous.get("content") != message.get("content"):
                raise ValueError("A dispatched image turn cannot be edited or retried")
        if any(messages.get(child, {}).get("corvus_arena_requested") for child in message.get("childrenIds", [])):
            raise ValueError("Images cannot be combined with Arena")
        expected.append(ref(file))
    # The mirrored messages array must be the same messages, not another source
    # of references or bytes. Other slots may never carry image references.
    for message in value.get("messages", []):
        if references(message) and message != messages.get(message.get("id")):
            raise ValueError("Inconsistent image history")
    count = len(expected) + sum(len(references(m)) for m in value.get("messages", []))
    if len(found) != count:
        raise ValueError("Invalid image reference location")


def protect_file(file):
    if is_reference(file):
        raise ValueError("Corvus image bindings cannot use generic file mutation")


async def upstream(method, path, *, body=None, headers=None, limit=LIMIT):
    # Paths are formed exclusively from validated server metadata, never a URL.
    if not path.startswith("/api/attachments") or ".." in path:
        raise HTTPException(503, "Image integration is unavailable")
    try:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                timeout=httpx.Timeout(20, connect=3), transport=httpx.AsyncHTTPTransport(retries=0)) as client:
            async with client.stream(method, BASE + path, content=body, headers=headers) as response:
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(data) + len(chunk) > limit:
                        raise HTTPException(502, "Invalid image service response")
                    data.extend(chunk)
                if response.status_code not in {200, 201}:
                    raise HTTPException(502, "Image service did not confirm the operation")
                return bytes(data), response.headers.get("content-type", "").split(";", 1)[0]
    except httpx.HTTPError:
        raise HTTPException(503, "Image service is unavailable; check operation status before retrying") from None


def bearer_mutation(request):
    # Reuse native user authentication, but cookie-only mutations are not allowed.
    if not request.headers.get("authorization", "").startswith("Bearer "):
        raise HTTPException(403, "Bearer authentication is required")


@router.post("/corvus-image/{chat_id}/{message_id}")
async def upload(request: Request, chat_id: str, message_id: str, user=Depends(get_verified_user)):
    enabled()
    bearer_mutation(request)
    if request.headers.get("x-corvus-arena") != "false":
        raise HTTPException(400, "Image and Arena cannot be combined")
    mime = request.headers.get("content-type", "")
    if mime not in {"image/png", "image/jpeg"}:
        raise HTTPException(400, "Only PNG/JPEG images are supported")
    with get_db() as db:
        chat, message = owned(db, user.id, chat_id, message_id)
        if any(chat.chat.get("history", {}).get("messages", {}).get(child, {}).get("corvus_arena_requested") for child in message.get("childrenIds", [])):
            raise HTTPException(400, "Images cannot be combined with Arena")
        if not isinstance(message.get("content"), str) or not message["content"].strip():
            raise HTTPException(400, "Include accompanying text for the image")
        if message.get("files") or not message.get("corvus_image_pending"):
            raise HTTPException(409, "Image turn is not pending")
    data = bytearray()
    async def consume():
        async for chunk in request.stream():
            if len(data) + len(chunk) > LIMIT:
                raise HTTPException(413, "Image is too large")
            data.extend(chunk)
    try:
        await asyncio.wait_for(consume(), 10)
    except asyncio.TimeoutError:
        raise HTTPException(408, "Image upload timed out") from None
    if not data or not (data.startswith(b"\x89PNG\r\n\x1a\n") if mime == "image/png" else data.startswith(b"\xff\xd8\xff")):
        raise HTTPException(400, "Invalid image format")
    instance = namespace()
    operation = hashlib.sha256(json.dumps([instance, user.id, chat_id, message_id], separators=(",", ":")).encode()).hexdigest()
    file_id = str(UUID(operation[:32]))
    digest = hashlib.sha256(data).hexdigest()
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        owned(db, user.id, chat_id, message_id)
        file = db.get(File, file_id)
        if file:
            if (not is_reference(file) or file.user_id != user.id
                    or any(file.meta.get(key) != value for key, value in {
                        "instance": instance, "chat_id": chat_id, "message_id": message_id,
                        "operation": operation, "digest": digest, "mime": mime}.items())
                    or file.meta.get("state") not in {"PENDING", "READY"}):
                raise HTTPException(409, "Image operation conflict")
            if file.meta["state"] == "READY":
                return ref(file)
        else:
            file = File(id=file_id, user_id=user.id, path=None, data={}, filename="image", created_at=int(time.time()), updated_at=int(time.time()), meta={
                "provider": PROVIDER, "instance": instance, "chat_id": chat_id, "message_id": message_id,
                "operation": operation, "digest": digest, "mime": mime, "size": len(data), "state": "PENDING"})
            db.add(file)
        db.commit()
    # Lost response leaves a durable PENDING row; same operation reuses A3 ID.
    raw, _ = await upstream("POST", "/api/attachments?filename=image", body=bytes(data),
        headers={"content-type": mime, "x-corvus-image-operation": operation}, limit=4096)
    try:
        result = json.loads(raw)
        attachment_id = result["attachment_id"]
        if len(attachment_id) != 32 or any(c not in "0123456789abcdef" for c in attachment_id) or result["media_type"] != mime or result["size_bytes"] != len(data) or result["blob_status"] != "PRESENT":
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise HTTPException(502, "Invalid image service response") from None
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        file = db.get(File, file_id)
        owned(db, user.id, chat_id, message_id)
        if file.meta["state"] not in {"PENDING", "READY"}:
            raise HTTPException(409, "Image operation is no longer available")
        file.meta = {**file.meta, "state": "READY", "attachment_id": attachment_id}
        db.commit()
        return ref(file)


async def content(file_id, user):
    enabled()
    with get_db() as db:
        file = db.get(File, file_id)
        authority(db, file, user.id)
        meta = dict(file.meta)
    raw, mime = await upstream("GET", "/api/attachments/" + meta["attachment_id"] + "/content")
    if mime != meta["mime"] or len(raw) != meta["size"] or hashlib.sha256(raw).hexdigest() != meta["digest"]:
        raise HTTPException(502, "Image is unavailable")
    with get_db() as db:
        authority(db, db.get(File, file_id), user.id)
    return Response(raw, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


def revoke(file_id, user):
    enabled()
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        file = db.get(File, file_id)
        authority(db, file, user.id)
        file.meta = {**file.meta, "state": "REVOKED"}
        db.commit()
    # Logical revocation only: blobs can be shared or canonically retained.
    return {"status": True}


def claim(user_id, chat_id, assistant_id, image_ref):
    enabled()
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        chat = db.get(Chat, uid(chat_id))
        assistant = (chat.chat.get("history", {}).get("messages", {}).get(assistant_id)
                     if chat and chat.user_id == user_id else None)
        if not assistant or assistant.get("role") != "assistant":
            raise ValueError("Invalid image turn")
        file = db.get(File, image_ref.get("corvus_ref"))
        _, message = authority(db, file, user_id)
        if (assistant.get("model") != "corvus_pipe" or file.meta["chat_id"] != chat_id
                or assistant.get("parentId") != message["id"]
                or image_ref != ref(file) or file.meta["state"] != "READY"):
            raise ValueError("Image turn cannot be dispatched again; reconcile its status")
        file.meta = {**file.meta, "state": "CLAIMED"}
        db.commit()
        return file.id, file.meta["attachment_id"], message["content"]


def finish(file_id, result=None):
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        file = db.get(File, file_id)
        if not file or file.meta["state"] != "CLAIMED":
            return
        confirmed = isinstance(result, dict) and type(result.get("user_message_id")) is int and type(result.get("assistant_message_id")) is int
        file.meta = {**file.meta, "state": "COMMITTED" if confirmed else "UNCERTAIN",
                     "canonical_user": result.get("user_message_id") if confirmed else None,
                     "canonical_assistant": result.get("assistant_message_id") if confirmed else None}
        db.commit()


@router.get("/corvus-image/{chat_id}/{message_id}")
async def operation(request: Request, chat_id: str, message_id: str, user=Depends(get_verified_user)):
    enabled()
    bearer_mutation(request)
    instance = namespace()
    op = hashlib.sha256(json.dumps([instance, user.id, chat_id, message_id], separators=(",", ":")).encode()).hexdigest()
    file_id = str(UUID(op[:32]))
    with get_db() as db:
        owned(db, user.id, chat_id, message_id)
        file = db.get(File, file_id)
        if (not is_reference(file) or file.user_id != user.id
                or any(file.meta.get(key) != value for key, value in {
                    "instance": instance, "chat_id": chat_id, "message_id": message_id,
                    "operation": op}.items())):
            raise HTTPException(404, "Image operation is unavailable")
        meta = dict(file.meta)
        if meta["state"] != "PENDING":
            return {"state": meta["state"], "reference": ref(file) if meta["state"] in {"READY", "COMMITTED", "UNCERTAIN"} else None}
    raw, _ = await upstream("GET", "/api/attachments/operations/" + op, limit=4096)
    try:
        result = json.loads(raw)
        attachment_id = result["attachment_id"]
        if (result["sha256"] != meta["digest"] or result["media_type"] != meta["mime"]
                or result["size_bytes"] != meta["size"] or result["blob_status"] != "PRESENT"
                or len(attachment_id) != 32 or any(c not in "0123456789abcdef" for c in attachment_id)):
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise HTTPException(502, "Image operation could not be reconciled") from None
    with get_db() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        owned(db, user.id, chat_id, message_id)
        file = db.get(File, file_id)
        if file.meta["state"] != "PENDING":
            raise HTTPException(409, "Image operation changed")
        file.meta = {**file.meta, "attachment_id": attachment_id, "state": "READY"}
        db.commit()
        return {"state": "READY", "reference": ref(file)}


def current_image(user_id, chat_id, assistant_id, content, arena):
    """Resolve only the actual parent of this response, never historical images."""
    with get_db() as db:
        chat = db.get(Chat, uid(chat_id))
        assistant = (chat.chat.get("history", {}).get("messages", {}).get(assistant_id)
                     if chat and chat.user_id == user_id else None)
        if not assistant or assistant.get("role") != "assistant":
            raise ValueError("A saved owned response is required")
        message = chat.chat.get("history", {}).get("messages", {}).get(assistant.get("parentId"), {})
        images = message.get("files", []) or []
        if message.get("corvus_image_pending") and not images:
            raise ValueError("Image upload is not confirmed; reconcile before sending")
        if not images:
            # Removing a reference must not release an uncertain dispatch hold.
            for prior in db.query(File).filter_by(user_id=user_id).all():
                if (is_reference(prior) and prior.meta.get("chat_id") == chat_id
                        and prior.meta.get("message_id") == message.get("id")
                        and prior.meta.get("state") in {"CLAIMED", "UNCERTAIN", "COMMITTED"}):
                    raise ValueError("Image turn already dispatched; do not retry automatically")
            return None
        if arena:
            raise ValueError("Images cannot be combined with Arena")
        if len(images) != 1 or message.get("content") != content:
            raise ValueError("Invalid current image turn")
        image = dict(images[0])
    return claim(user_id, chat_id, assistant_id, image)


def mutation_actor(chat, user, payload):
    """Retain native admin text operations, but never grant an image-owner bypass."""
    reject_bytes(payload)
    pending = any(message.get("corvus_image_pending") for message in
                  (chat.chat or {}).get("history", {}).get("messages", {}).values())
    if chat.user_id != user.id and (pending or references(chat.chat) or references(payload)):
        raise HTTPException(404, "Image binding is unavailable")
