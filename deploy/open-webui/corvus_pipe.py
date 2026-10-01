"""
title: Corvus OW1
description: Text-only adapter to the authoritative Corvus conversation runtime.
version: 0.1.0
required_open_webui_version: 0.6.5
"""

import hashlib
import json
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, Field


CORVUS_CHAT_URL = "http://127.0.0.1:8096/api/chat"
UNCERTAIN_RESULT = (
    "Corvus did not confirm this turn. It may already have been saved. "
    "Check Corvus before sending again; do not retry or regenerate automatically."
)


def _identity(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def corvus_session_id(instance_id, user_id, chat_id):
    """Versioned, unambiguous mapping; never accept a socket session ID."""
    if not all(_identity(value) for value in (instance_id, user_id, chat_id)):
        raise ValueError("OW1 requires INSTANCE_ID, an authenticated user, and a saved chat.")
    try:
        # v0.6.5 saved chats use canonical UUIDs; local/temporary IDs fail closed.
        saved_chat = str(UUID(chat_id)) == chat_id
    except ValueError:
        saved_chat = False
    if not saved_chat:
        raise ValueError("OW1 requires a saved chat; temporary/local chats are unsupported.")
    identity = json.dumps(
        [instance_id, user_id, chat_id], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return "ow1:" + hashlib.sha256(identity).hexdigest()


def _reject_unsupported(source):
    # Inspect both the body and retained metadata: v0.6.5 pops feature/file/tool
    # fields before invoking a Pipe, and may already have transformed messages.
    for key in (
        "files", "attachments", "attachment_id", "images", "audio", "video",
        "tools", "tool_ids", "tool_servers", "tool_calls", "functions",
        "function_call", "function_calling", "tool_choice", "operation", "action",
        "regenerate", "branch", "parent_id", "parent_message_id", "continue",
    ):
        if source.get(key) not in (None, False, "", [], {}):
            raise ValueError("OW1 supports ordinary text turns only; this operation is unsupported.")
    features = source.get("features")
    if features is not None and (
        not isinstance(features, dict) or any(features.values())
    ):
        raise ValueError("OW1 does not support Open WebUI search, media, or tool features.")
    if source.get("modalities") not in (None, [], ["text"]):
        raise ValueError("OW1 supports text only.")
    if source.get("n", 1) != 1:
        raise ValueError("OW1 supports one response per turn.")


class Pipe:
    class Valves(BaseModel):
        INSTANCE_ID: str = Field(
            default="", description="Required stable unique ID for this Open WebUI installation."
        )
        WEB_MODE: Literal["off", "on", "auto"] = Field(
            default="auto", description="Corvus web mode, controlled by the administrator."
        )
        TIMEOUT_SECONDS: float = Field(default=300, ge=1, le=600)

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __chat_id__: str = None,
        __metadata__: dict = None,
        __task__: str = None,
        __task_body__: dict = None,
        __files__: list = None,
        __tools__: dict = None,
    ) -> str:
        if not isinstance(body, dict):
            raise ValueError("OW1 requires a text chat request.")
        metadata_sources = [__metadata__, body.get("metadata")]
        for metadata in metadata_sources:
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError("OW1 requires valid chat metadata.")
        sources = [body] + [item for item in metadata_sources if item is not None]

        # Suppress *all* tasks, including unknown future task labels, before
        # identity validation or I/O. Empty output is local to Open WebUI.
        if __task__ is not None or __task_body__ is not None or any(
            source.get("task") is not None or source.get("task_body") is not None
            for source in sources
        ):
            return ""

        for source in sources:
            _reject_unsupported(source)
        if __files__ or __tools__:
            raise ValueError("OW1 does not support files or tools.")
        params = body.get("params")
        if params is not None:
            if not isinstance(params, dict):
                raise ValueError("OW1 requires valid request parameters.")
            _reject_unsupported(params)

        user_id = (__user__ or {}).get("id") if isinstance(__user__, dict) else None
        chat_ids = [__chat_id__] + [source.get("chat_id") for source in sources]
        chat_ids = [value for value in chat_ids if value is not None]
        chat_id = chat_ids[0] if chat_ids else None
        if any(value != chat_id for value in chat_ids) or any(
            source.get("user_id", user_id) != user_id for source in sources
        ):
            raise ValueError("OW1 received inconsistent chat identity.")
        session_id = corvus_session_id(self.valves.INSTANCE_ID, user_id, chat_id)
        if self.valves.WEB_MODE not in {"off", "on", "auto"}:
            raise ValueError("OW1 WEB_MODE must be off, on, or auto.")

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("OW1 requires a current user text message.")
        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in ("system", "user", "assistant")
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("OW1 does not support media or tool messages.")
            _reject_unsupported(message)
        current = messages[-1]
        if current["role"] != "user" or not current["content"].strip():
            raise ValueError("OW1 requires a new, nonempty user text turn.")

        payload = {
            "session_id": session_id,
            "message": current["content"],
            "web_mode": self.valves.WEB_MODE,
        }
        # No redirects, environment proxies, or HTTP transport retries. Corvus
        # can persist before the caller times out; OW1 has no idempotency key.
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.valves.TIMEOUT_SECONDS, connect=5),
                follow_redirects=False,
                trust_env=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.post(CORVUS_CHAT_URL, json=payload)
        except httpx.TimeoutException:
            raise ValueError("Corvus request timed out. " + UNCERTAIN_RESULT) from None
        except httpx.HTTPError:
            raise ValueError("Corvus request failed. " + UNCERTAIN_RESULT) from None

        if response.status_code != 200:
            # Never include response.text, exception strings, or backend error fields.
            raise ValueError("Corvus returned an unsuccessful response. " + UNCERTAIN_RESULT)
        try:
            result = response.json()
        except (ValueError, UnicodeError):
            raise ValueError("Corvus returned an invalid response. " + UNCERTAIN_RESULT) from None
        if not isinstance(result, dict):
            raise ValueError("Corvus returned an invalid response. " + UNCERTAIN_RESULT)
        status = result.get("status")
        reply = result.get("reply")
        if (
            result.get("session_id") != session_id
            or not isinstance(status, dict)
            or status.get("overall") not in ("OK", "DEGRADED")
            or status.get("model") != "OK"
            or status.get("persistence") != "NORMAL"
            or not isinstance(reply, str)
            or not reply.strip()
        ):
            raise ValueError("Corvus did not return a confirmed reply. " + UNCERTAIN_RESULT)
        return reply
