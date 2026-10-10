"""Durable single-attempt async submission; Lab lifecycle is disabled by default."""

import asyncio
from dataclasses import dataclass
from enum import Enum
import json
from urllib.parse import quote
import uuid

import httpx
from starlette.concurrency import run_in_threadpool

from app import hindsight_shadow as shadow
from app.retain_ledger import LedgerError, payload_fingerprint


CONTRACT_VERSION = 1
SUBMISSION_DEADLINE_SECONDS = 10


class SubmissionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"
    FAILED_TO_SUBMIT = "FAILED_TO_SUBMIT"
    INTENT_DURABILITY_FAILED = "INTENT_DURABILITY_FAILED"


@dataclass(frozen=True)
class SubmissionResult:
    status: SubmissionStatus
    operation_id: str | None = None
    error: str | None = None
    http_status: int | None = None
    acceptance_unknown: bool = False
    outcome_durable: bool = False
    ledger_error: str | None = None


def build_async_request(intent, item):
    """Validate replay material before constructing the exact audited body."""
    if intent.contract_version != CONTRACT_VERSION:
        raise LedgerError("unsupported retain contract version")
    if (not isinstance(item, dict) or item.get("document_id") != intent.document_id or
        payload_fingerprint(intent.bank, item, intent.contract_version) != intent.payload_fingerprint):
        raise LedgerError("retain payload fingerprint mismatch")
    if str(uuid.UUID(intent.operation_id)) != intent.operation_id:
        raise LedgerError("noncanonical operation UUID")
    # An owned JSON copy keeps caller mutation out of an in-flight request.
    return {"items": [json.loads(json.dumps(item, ensure_ascii=False, allow_nan=False))],
            "async": True, "operation_id": intent.operation_id}


def _validate_client(base_url, deadline_seconds):
    url = httpx.URL(base_url)
    if (url.scheme not in ("http", "https") or not url.host or
        url.path not in ("", "/") or url.query or url.fragment):
        raise ValueError("expected HTTP API origin")
    if (type(deadline_seconds) not in (int, float) or
        not 0 < deadline_seconds <= 60):
        raise ValueError("invalid bounded submission deadline")


async def _outcome(ledger, intent, status, *, error=None, http_status=None,
                   acceptance_unknown=False):
    """Outcome append failure never erases the durable pre-send identity."""
    try:
        if status == SubmissionStatus.ACCEPTED:
            await run_in_threadpool(ledger.record_submission_accepted, intent.operation_id)
        elif acceptance_unknown:
            await run_in_threadpool(ledger.record_submission_ambiguous, intent.operation_id, error=error)
        else:
            await run_in_threadpool(ledger.record_submission_failed, intent.operation_id,
                                   failure_kind=status.value, error=error, http_status=http_status)
    except Exception as exc:
        return SubmissionResult(status, intent.operation_id, error, http_status,
                                acceptance_unknown, ledger_error=type(exc).__name__)
    return SubmissionResult(status, intent.operation_id, error, http_status,
                            acceptance_unknown, outcome_durable=True)


def _validate_ack(response, intent):
    body = response.json()
    if (not isinstance(body, dict) or body.get("success") is not True or
        body.get("async") is not True or body.get("bank_id") != intent.bank or
        type(body.get("items_count")) is not int or body["items_count"] != 1):
        raise ValueError("invalid async retain acknowledgement")
    returned = body.get("operation_id")
    if not isinstance(returned, str) or str(uuid.UUID(returned)) != intent.operation_id:
        raise ValueError("operation UUID mismatch")
    # A single-item/single-strategy request cannot acknowledge unrelated parents.
    if body.get("operation_ids") not in (None, [intent.operation_id]):
        raise ValueError("unexpected operation UUIDs")


def _classify_response(response, intent):
    code = response.status_code
    if 400 <= code < 500 and code != 408:
        return SubmissionStatus.REJECTED, dict(error=f"HTTP_{code}", http_status=code)
    if not 200 <= code < 300:
        return SubmissionStatus.AMBIGUOUS, dict(error=f"HTTP_{code}", http_status=code,
                                              acceptance_unknown=True)
    try:
        _validate_ack(response, intent)
    except (ValueError, TypeError, AttributeError):
        # Reject this ACK as proof, without asserting the POST was not committed.
        return SubmissionStatus.REJECTED, dict(error="INVALID_ACK", http_status=code,
                                              acceptance_unknown=True)
    return SubmissionStatus.ACCEPTED, dict(http_status=code)


async def _attempt(ledger, intent, item, *, base_url, deadline_seconds, transport):
    try:
        states = await run_in_threadpool(ledger.read)
        state = states.get(intent.operation_id)
        if state is None or state.intent != intent:
            raise LedgerError("intent is not durably recorded")
    except Exception as exc:
        return SubmissionResult(SubmissionStatus.INTENT_DURABILITY_FAILED, intent.operation_id,
                                "INTENT_NOT_TRUSTWORTHY", ledger_error=type(exc).__name__)
    try:
        if not state.unresolved:
            raise LedgerError("terminal retain requires status/retry reconciliation, not submission")
        body = build_async_request(intent, item)
        _validate_client(base_url, deadline_seconds)
    except Exception:
        return await _outcome(ledger, intent, SubmissionStatus.FAILED_TO_SUBMIT,
                              error="SUBMISSION_PRECONDITION_FAILED")
    attempted = False
    classified = None
    try:
        async with asyncio.timeout(deadline_seconds):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(deadline_seconds, connect=min(2, deadline_seconds)),
                trust_env=False, follow_redirects=False,
                transport=transport if transport is not None else httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                attempted = True
                response = await client.post(
                    f"{base_url.rstrip('/')}/v1/default/banks/{quote(intent.bank, safe='')}/memories",
                    json=body,
                )
                classified = _classify_response(response, intent)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.InvalidURL):
        if classified is None:
            classified = SubmissionStatus.FAILED_TO_SUBMIT, dict(error="PRE_SEND_TRANSPORT_FAILURE")
    except asyncio.CancelledError:
        if classified is not None:
            status, details = classified
            await _outcome(ledger, intent, status, **details)
        elif attempted:
            await _outcome(ledger, intent, SubmissionStatus.AMBIGUOUS,
                           error="CLIENT_CANCELLED", acceptance_unknown=True)
        raise
    except Exception:
        if classified is None:
            classified = (
                SubmissionStatus.AMBIGUOUS if attempted else SubmissionStatus.FAILED_TO_SUBMIT,
                dict(error="TRANSPORT_COMPLETION_UNKNOWN" if attempted else "CLIENT_SETUP_FAILED",
                     acceptance_unknown=attempted),
            )
    # The deadline bounds HTTP only. A received ACK survives client-close failure,
    # and outcome fsync must not be cancelled/reclassified by the HTTP deadline.
    status, details = classified
    return await _outcome(ledger, intent, status, **details)


async def submit_async_retain(turn, ledger, *, operation_id=None, bank=shadow.BANK,
                              base_url=shadow.BASE_URL, deadline_seconds=SUBMISSION_DEADLINE_SECONDS,
                              transport=None):
    """Record/fsync an intent before exactly one POST; no automatic resubmission."""
    try:
        _validate_client(base_url, deadline_seconds)
        item = await run_in_threadpool(shadow._load_retain_item, turn)
        if item is None:
            raise ValueError("missing canonical turn")
        payload_fingerprint(bank, item, CONTRACT_VERSION)  # Validate material before UUID creation.
        item = json.loads(json.dumps(item, ensure_ascii=False, allow_nan=False))
        operation_id = str(uuid.uuid4()) if operation_id is None else str(uuid.UUID(operation_id))
    except Exception:
        return SubmissionResult(SubmissionStatus.FAILED_TO_SUBMIT, error="INVALID_CANONICAL_ITEM_OR_CLIENT")
    try:
        await run_in_threadpool(
            ledger.record_intent, user_message_id=turn.user_message_id,
            assistant_message_id=turn.assistant_message_id, session_id=turn.session_id,
            bank=bank, item=item, operation_id=operation_id, contract_version=CONTRACT_VERSION,
        )
        # Recover the original intent timestamp if this was a duplicate client UUID.
        intent = (await run_in_threadpool(ledger.read))[operation_id].intent
    except Exception as exc:
        return SubmissionResult(SubmissionStatus.INTENT_DURABILITY_FAILED, operation_id,
                                "INTENT_DURABILITY_FAILED", ledger_error=type(exc).__name__)
    return await _attempt(ledger, intent, item, base_url=base_url,
                          deadline_seconds=deadline_seconds, transport=transport)


async def replay_async_retain(operation_id, ledger, *, base_url=shadow.BASE_URL,
                              deadline_seconds=SUBMISSION_DEADLINE_SECONDS, transport=None):
    """Load an existing intent and canonical item; never create a replacement UUID."""
    try:
        operation_id = str(uuid.UUID(operation_id))
        state = (await run_in_threadpool(ledger.read)).get(operation_id)
        if state is None:
            raise LedgerError("missing intent")
        intent = state.intent
    except Exception as exc:
        return SubmissionResult(SubmissionStatus.INTENT_DURABILITY_FAILED, operation_id,
                                "INTENT_NOT_TRUSTWORTHY", ledger_error=type(exc).__name__)
    turn = shadow.ShadowTurn(intent.session_id, intent.user_message_id,
                            intent.assistant_message_id, "", ())
    try:
        item = await run_in_threadpool(shadow._load_retain_item, turn)
    except Exception:
        item = None
    return await _attempt(ledger, intent, item, base_url=base_url,
                          deadline_seconds=deadline_seconds, transport=transport)
