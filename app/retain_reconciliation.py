"""Bounded offline async-retain reconciliation; no lifecycle hooks or replay."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from urllib.parse import quote
import uuid

import httpx
from starlette.concurrency import run_in_threadpool

from app import async_retain, hindsight_shadow as shadow
from app.durable_jsonl import _object, _invalid_constant
from app.retain_ledger import LedgerError, normalize_status_observation


STATUS_DEADLINE_SECONDS = 10


class ReconciliationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REPLAY_NEEDED = "REPLAY_NEEDED"
    STATUS_AMBIGUOUS = "STATUS_AMBIGUOUS"
    STATUS_ERROR = "STATUS_ERROR"


@dataclass(frozen=True)
class OperationStatusRead:
    observation: dict | None = None
    error: str | None = None
    ambiguous: bool = False
    http_status: int | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    status: ReconciliationStatus
    operation_id: str
    observation: dict | None = None
    error: str | None = None
    http_status: int | None = None
    outcome_durable: bool = False


def _parse_response(response, bank, operation_id):
    if not 200 <= response.status_code < 300:
        return OperationStatusRead(error=f"HTTP_{response.status_code}", http_status=response.status_code)
    try:
        body = json.loads(response.content, object_pairs_hook=_object, parse_constant=_invalid_constant)
        if isinstance(body, dict) and "bank_id" in body and body["bank_id"] != bank:
            raise LedgerError("wrong bank")
        observation = normalize_status_observation(operation_id, body)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return OperationStatusRead(error="INVALID_STATUS_RESPONSE", http_status=response.status_code)
    return OperationStatusRead(observation, http_status=response.status_code)


async def get_operation_status(bank, operation_id, *, base_url=shadow.BASE_URL,
                               deadline_seconds=STATUS_DEADLINE_SECONDS, transport=None):
    """Exactly one status GET; 404 is an API error, not the JSON not_found state.

    This client makes no submission. Hindsight's status API itself may repair
    parent bookkeeping; callers must account for that when eventually deployed.
    """
    try:
        operation_id = str(uuid.UUID(operation_id))
        if not isinstance(bank, str) or not bank.strip():
            raise ValueError("invalid bank")
        async_retain._validate_client(base_url, deadline_seconds)
    except Exception:
        return OperationStatusRead(error="INVALID_STATUS_REQUEST")
    result = None
    try:
        async with asyncio.timeout(deadline_seconds):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(deadline_seconds, connect=min(2, deadline_seconds)),
                trust_env=False, follow_redirects=False,
                transport=transport if transport is not None else httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/v1/default/banks/{quote(bank, safe='')}/operations/{operation_id}")
                result = _parse_response(response, bank, operation_id)
    except (TimeoutError, httpx.RequestError):
        if result is None:
            result = OperationStatusRead(error="STATUS_TRANSPORT_UNKNOWN", ambiguous=True)
    except Exception:
        if result is None:
            result = OperationStatusRead(error="STATUS_CLIENT_ERROR")
    return result


def select_unresolved(states, max_operations=10):
    """Pure selection: oldest recorded intent first, UUID breaks timestamp ties."""
    if type(max_operations) is not int or max_operations < 0:
        raise ValueError("max_operations must be a nonnegative integer")
    return sorted((state.intent for state in states.values() if state.unresolved),
                  key=lambda intent: (datetime.fromisoformat(intent.recorded_at), intent.operation_id))[:max_operations]


async def reconcile_operation(operation_id, ledger, *, base_url=shadow.BASE_URL,
                              deadline_seconds=STATUS_DEADLINE_SECONDS, transport=None):
    """Look up the recorded UUID first. Never submit, retry or invent payloads."""
    try:
        operation_id = str(uuid.UUID(operation_id))
        state = (await run_in_threadpool(ledger.read)).get(operation_id)
        if state is None:
            raise LedgerError("missing intent")
    except Exception:
        return ReconciliationResult(ReconciliationStatus.STATUS_ERROR, operation_id,
                                    error="INTENT_NOT_TRUSTWORTHY")
    if not state.unresolved:
        return ReconciliationResult(ReconciliationStatus(state.terminal_status.upper()), operation_id,
                                    state.status_observation, outcome_durable=True)
    read = await get_operation_status(state.intent.bank, operation_id, base_url=base_url,
                                     deadline_seconds=deadline_seconds, transport=transport)
    if read.observation is None:
        status = ReconciliationStatus.STATUS_AMBIGUOUS if read.ambiguous else ReconciliationStatus.STATUS_ERROR
        return ReconciliationResult(status, operation_id, error=read.error, http_status=read.http_status)
    observation = read.observation
    try:
        await run_in_threadpool(
            ledger.record_status, operation_id, observation["status"],
            error=observation.get("error_message"), retry_count=observation.get("retry_count"),
            next_retry_at=observation.get("next_retry_at"), observation=observation,
        )
        # Preserve a concurrently recorded terminal outcome: not_found cannot
        # erase completion or authorize replay after another observer finishes.
        latest = (await run_in_threadpool(ledger.read))[operation_id]
        if latest.intent != state.intent:
            raise LedgerError("intent changed")
    except Exception:
        return ReconciliationResult(ReconciliationStatus.STATUS_ERROR, operation_id, observation,
                                    error="STATUS_DURABILITY_FAILED", http_status=read.http_status)
    if latest.terminal_status is not None:
        status = ReconciliationStatus(latest.terminal_status.upper())
    elif observation["status"] == "not_found":
        try:
            turn = shadow.ShadowTurn(state.intent.session_id, state.intent.user_message_id,
                                     state.intent.assistant_message_id, "", ())
            item = await run_in_threadpool(shadow._load_retain_item, turn)
            async_retain.build_async_request(state.intent, item)
        except Exception:
            return ReconciliationResult(ReconciliationStatus.STATUS_ERROR, operation_id, observation,
                                        error="REPLAY_PAYLOAD_UNRECOVERABLE", http_status=read.http_status,
                                        outcome_durable=True)
        try:
            latest = (await run_in_threadpool(ledger.read))[operation_id]
            if latest.intent != state.intent:
                raise LedgerError("intent changed during reconstruction")
        except Exception:
            return ReconciliationResult(ReconciliationStatus.STATUS_ERROR, operation_id, observation,
                                        error="INTENT_NOT_TRUSTWORTHY", http_status=read.http_status)
        status = (ReconciliationStatus(latest.terminal_status.upper()) if latest.terminal_status
                  else ReconciliationStatus.REPLAY_NEEDED)
    else:
        status = ReconciliationStatus(observation["status"].upper())
    return ReconciliationResult(status, operation_id, observation, observation.get("error_message"),
                                read.http_status, outcome_durable=True)


async def reconcile_unresolved(ledger, *, max_operations=10, base_url=shadow.BASE_URL,
                               deadline_seconds=STATUS_DEADLINE_SECONDS, transport=None):
    """One finite pass, at most N operations, no sleep, retries or retain replay.

    Ledger reconstruction still reads all history; the limit bounds operations
    and HTTP attempts, not file size. Untrustworthy history raises before HTTP.
    """
    intents = select_unresolved(await run_in_threadpool(ledger.read), max_operations)
    results = []
    for intent in intents:
        results.append(await reconcile_operation(intent.operation_id, ledger, base_url=base_url,
                                                  deadline_seconds=deadline_seconds, transport=transport))
    return tuple(results)
