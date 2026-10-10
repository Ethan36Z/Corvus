"""Offline retain intent/outcome persistence; no HTTP, SQLite or lifecycle hooks.

Use the existing private shadow JSONL path explicitly. Legacy records are retained
and ignored by the reducer. An unreadable/damaged ledger raises instead of yielding
a trusted partial state. This module is not used by the live retain path yet.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from app.durable_jsonl import append_jsonl, read_jsonl


RECORD_TYPE = "retain_ledger"
LEDGER_VERSION = 1
EVENTS = {"RETAIN_INTENT", "RETAIN_SUBMISSION_ACCEPTED",
          "RETAIN_SUBMISSION_AMBIGUOUS", "RETAIN_SUBMISSION_FAILED", "RETAIN_STATUS"}
STATUSES = {"pending", "processing", "completed", "failed", "cancelled", "not_found"}
TERMINAL = {"completed", "failed", "cancelled"}


class LedgerError(ValueError):
    """Untrustworthy input/state; never treat this as an empty or completed ledger."""


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise LedgerError("expected nonempty text")
    return value


def _positive_int(value):
    if type(value) is not int or value <= 0:
        raise LedgerError("expected positive integer")
    return value


def _operation_id(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise LedgerError("operation_id must be a UUID") from exc


def _timestamp(value):
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timezone required")
        return timestamp.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError) as exc:
        raise LedgerError("expected timezone-aware ISO timestamp") from exc


def _json_value(value):
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise LedgerError("JSON object keys must be strings")
        for child in value.values():
            _json_value(child)
    elif isinstance(value, list):
        for child in value:
            _json_value(child)
    elif value is not None and type(value) not in (str, bool, int, float):
        raise LedgerError("payload must contain only JSON values")


def payload_fingerprint(bank, item, contract_version=1):
    """SHA-256 of the exact single-item async contract, excluding operation UUID.

    All item fields (including omitted versus explicit null fields) participate.
    Event times, HTTP timing and operation identity are not payload material.
    """
    _text(bank)
    _positive_int(contract_version)
    if not isinstance(item, dict):
        raise LedgerError("retain item must be an object")
    _text(item.get("document_id"))
    _text(item.get("content"))
    material = {"bank": bank, "contract_version": contract_version,
                "request": {"items": [item], "async": True}}
    try:
        _json_value(material)
        data = json.dumps(material, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise LedgerError("retain payload is not canonical JSON") from exc
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class RetainIntent:
    operation_id: str
    user_message_id: int
    assistant_message_id: int
    session_id: str
    bank: str
    document_id: str
    contract_version: int
    payload_fingerprint: str
    recorded_at: str


@dataclass(frozen=True)
class RetainState:
    intent: RetainIntent
    submission_state: str = "NOT_ATTEMPTED"
    last_hindsight_status: str | None = None
    terminal_status: str | None = None
    next_retry_at: str | None = None
    retry_count: int | None = None
    error: str | None = None
    http_status: int | None = None
    updated_at: str | None = None

    @property
    def unresolved(self):
        return self.terminal_status is None


def _validate_event(event):
    if not isinstance(event, dict):
        raise LedgerError("ledger record must be an object")
    if event.get("record_type") != RECORD_TYPE:
        # Existing comparison records have no record_type; outcomes have this one.
        if (event.get("record_type") in (None, "retain_outcome") and
            not {"ledger_version", "event_type", "operation_id"} & event.keys()):
            return None
        raise LedgerError("unknown record type")
    common = {"record_type", "ledger_version", "event_type", "operation_id", "recorded_at"}
    kind = event.get("event_type")
    if (type(event.get("ledger_version")) is not int or
        event["ledger_version"] != LEDGER_VERSION or not isinstance(kind, str) or kind not in EVENTS):
        raise LedgerError("unknown ledger version/event")
    extra = {
        "RETAIN_INTENT": {"user_message_id", "assistant_message_id", "session_id", "bank",
                          "document_id", "contract_version", "payload_fingerprint"},
        "RETAIN_SUBMISSION_ACCEPTED": set(),
        "RETAIN_SUBMISSION_AMBIGUOUS": {"error"},
        "RETAIN_SUBMISSION_FAILED": {"failure_kind", "error", "http_status"},
        "RETAIN_STATUS": {"status", "next_retry_at", "retry_count", "error"},
    }[kind]
    if set(event) != common | extra:
        raise LedgerError("invalid ledger event fields")
    operation_id = _operation_id(event["operation_id"])
    if operation_id != event["operation_id"]:
        raise LedgerError("operation UUID must use canonical spelling")
    _timestamp(event["recorded_at"])
    if kind == "RETAIN_INTENT":
        user = _positive_int(event["user_message_id"])
        assistant = _positive_int(event["assistant_message_id"])
        if user >= assistant or event["document_id"] != f"corvus-lab:turn:{user}:{assistant}":
            raise LedgerError("invalid per-turn document identity")
        _text(event["session_id"])
        _text(event["bank"])
        _positive_int(event["contract_version"])
        if (not isinstance(event["payload_fingerprint"], str) or
            not re.fullmatch(r"[0-9a-f]{64}", event["payload_fingerprint"])):
            raise LedgerError("invalid payload fingerprint")
    if "error" in event and event["error"] is not None:
        _text(event["error"])
    if kind == "RETAIN_SUBMISSION_FAILED":
        if event["failure_kind"] not in ("REJECTED", "FAILED_TO_SUBMIT"):
            raise LedgerError("invalid submission failure kind")
        _text(event["error"])
        status = event["http_status"]
        if status is not None and (type(status) is not int or not 100 <= status <= 599):
            raise LedgerError("invalid HTTP status")
    if kind == "RETAIN_STATUS":
        if not isinstance(event["status"], str) or event["status"] not in STATUSES:
            raise LedgerError("invalid Hindsight status")
        if event["next_retry_at"] is not None:
            _timestamp(event["next_retry_at"])
        retry_count = event["retry_count"]
        if retry_count is not None and (type(retry_count) is not int or retry_count < 0):
            raise LedgerError("invalid retry count")
    return kind


def reduce_events(records):
    """Pure reducer. Corruption/conflicting identity raises; no partial result escapes.

    NOT_ATTEMPTED means no recorded submission result, not proof a POST never ran.
    Status observations can establish acceptance; not_found cannot erase completion.
    Failed/cancelled work becomes unresolved if a later explicit retry is observed.
    """
    states = {}
    for event in records:
        kind = _validate_event(event)
        if kind is None:
            continue
        operation_id = event["operation_id"]
        if kind == "RETAIN_INTENT":
            fields = {key: event[key] for key in RetainIntent.__dataclass_fields__}
            intent = RetainIntent(**fields)
            if operation_id in states:
                previous = states[operation_id].intent
                if replace(intent, recorded_at=previous.recorded_at) != previous:
                    raise LedgerError("operation UUID reused for a different intent")
            else:
                states[operation_id] = RetainState(intent, updated_at=intent.recorded_at)
            continue
        if operation_id not in states:
            raise LedgerError("outcome has no preceding intent")
        state = states[operation_id]
        changes = {"updated_at": event["recorded_at"]}
        if kind == "RETAIN_SUBMISSION_ACCEPTED":
            changes.update(submission_state="ACCEPTED", error=None, http_status=None)
        elif kind == "RETAIN_SUBMISSION_AMBIGUOUS":
            if state.submission_state != "ACCEPTED":
                changes.update(submission_state="AMBIGUOUS", error=event["error"], http_status=None)
        elif kind == "RETAIN_SUBMISSION_FAILED":
            changes.update(error=event["error"], http_status=event["http_status"])
            if state.submission_state != "ACCEPTED":
                changes["submission_state"] = event["failure_kind"]
        else:
            status = event["status"]
            if state.terminal_status == "completed" and status not in ("completed", "not_found"):
                raise LedgerError("contradictory status after completion")
            terminal = (state.terminal_status if status == "not_found"
                        else status if status in TERMINAL else None)
            changes.update(last_hindsight_status=status, terminal_status=terminal,
                           next_retry_at=event["next_retry_at"], retry_count=event["retry_count"],
                           error=event["error"])
            if status != "not_found":
                changes.update(submission_state="ACCEPTED", http_status=None)
        states[operation_id] = replace(state, **changes)
    return states


class RetainLedger:
    """Explicit-path primitive; construction does no I/O and has no live default."""

    def __init__(self, path):
        self.path = Path(path)

    def _append(self, kind, operation_id, recorded_at=None, **fields):
        event = {"record_type": RECORD_TYPE, "ledger_version": LEDGER_VERSION,
                 "event_type": kind, "operation_id": _operation_id(operation_id),
                 "recorded_at": _timestamp(recorded_at) if recorded_at is not None
                 else datetime.now(timezone.utc).isoformat(), **fields}
        _validate_event(event)
        append_jsonl(self.path, event, validate_records=reduce_events)
        return event

    def record_intent(self, *, user_message_id, assistant_message_id, session_id, bank,
                      item, operation_id=None, contract_version=1, recorded_at=None):
        operation_id = str(uuid.uuid4()) if operation_id is None else _operation_id(operation_id)
        event = self._append(
            "RETAIN_INTENT", operation_id, recorded_at, user_message_id=user_message_id,
            assistant_message_id=assistant_message_id, session_id=session_id, bank=bank,
            document_id=item.get("document_id") if isinstance(item, dict) else None,
            contract_version=contract_version,
            payload_fingerprint=payload_fingerprint(bank, item, contract_version),
        )
        return RetainIntent(**{key: event[key] for key in RetainIntent.__dataclass_fields__})

    def record_submission_accepted(self, operation_id, *, recorded_at=None):
        self._append("RETAIN_SUBMISSION_ACCEPTED", operation_id, recorded_at)

    def record_submission_ambiguous(self, operation_id, *, error=None, recorded_at=None):
        self._append("RETAIN_SUBMISSION_AMBIGUOUS", operation_id, recorded_at, error=error)

    def record_submission_failed(self, operation_id, *, failure_kind, error,
                                 http_status=None, recorded_at=None):
        self._append("RETAIN_SUBMISSION_FAILED", operation_id, recorded_at,
                     failure_kind=failure_kind, error=error, http_status=http_status)

    def record_status(self, operation_id, status, *, next_retry_at=None, retry_count=None,
                      error=None, recorded_at=None):
        self._append("RETAIN_STATUS", operation_id, recorded_at, status=status,
                     next_retry_at=_timestamp(next_retry_at) if next_retry_at is not None else None,
                     retry_count=retry_count, error=error)

    def read(self):
        """Read/reduce only; never create a missing file or repair a damaged one."""
        return reduce_events(read_jsonl(self.path))
