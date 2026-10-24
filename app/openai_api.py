"""Minimal standalone text API. Deliberately imports no conversation/memory runtime."""
import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
import json
import math
import os
import re
from time import monotonic
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError, field_validator, model_validator
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect

from app.api_auth import KeyConfigurationError, check_key_file
from app.foreground_activity import ForegroundActivityTracker
from app.model_client import ModelClientError, stateless_chat_completion


MAX_BODY = 131072
PRIVATE = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
TokenLimit = Annotated[StrictInt, Field(ge=1, le=1024)]
Count = Annotated[StrictInt, Field(ge=0)]
Text = Annotated[str, Field(min_length=1, max_length=131072)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Message(StrictModel):
    role: Literal['system', 'developer', 'user', 'assistant']
    content: Text

    @field_validator('content')
    @classmethod
    def valid_text(cls, value):
        value.encode('utf-8')
        return value


class ResponseFormat(StrictModel):
    type: Literal['text', 'json_object'] = 'text'


class ChatRequest(StrictModel):
    model: str = Field(min_length=1, max_length=128)
    messages: list[Message] = Field(min_length=1, max_length=64)
    stream: StrictBool = False
    n: Annotated[StrictInt, Field(ge=1, le=1)] = 1
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1, gt=0, le=1)
    max_tokens: TokenLimit = 512
    max_completion_tokens: TokenLimit | None = None
    stop: str | list[str] | None = None
    response_format: ResponseFormat = Field(default_factory=ResponseFormat)

    @model_validator(mode='after')
    def supported(self):
        if self.stream or {'max_tokens', 'max_completion_tokens'} <= self.model_fields_set:
            raise ValueError('unsupported or conflicting parameters')
        if self.stop is not None:
            stops = [self.stop] if isinstance(self.stop, str) else self.stop
            if not 1 <= len(stops) <= 4 or any(not 1 <= len(s) <= 128 for s in stops):
                raise ValueError('invalid stop')
            for s in stops:
                s.encode('utf-8')
        # Only a leading instruction prefix, then alternating user/assistant turns.
        turns = [m for m in self.messages if m.role not in ('system', 'developer')]
        prefix = len(self.messages) - len(turns)
        if (not turns or any(m.role not in ('system', 'developer') for m in self.messages[:prefix])
                or turns != self.messages[prefix:]
                or any(m.role != ('user' if i % 2 == 0 else 'assistant') for i, m in enumerate(turns))
                or turns[-1].role != 'user'):
            raise ValueError('unsupported message order')
        return self

    def upstream(self):
        instructions, turns = [], []
        for m in self.messages:
            if m.role in ('system', 'developer'):
                instructions.append(m.content)
            else:
                turns.append(m.model_dump())
        messages = ([{'role': 'system', 'content': '\n\n'.join(instructions)}] if instructions else []) + turns
        payload = {'model': self.model, 'messages': messages, 'temperature': self.temperature,
                   'top_p': self.top_p, 'max_tokens': self.max_completion_tokens or self.max_tokens,
                   'response_format': self.response_format.model_dump(), 'n': 1}
        if self.stop is not None:
            payload['stop'] = self.stop
        return payload


class APIError(Exception):
    def __init__(self, status, code, message, kind='invalid_request_error'):
        self.status, self.code, self.message, self.kind = status, code, message, kind
        self.retry_after = 10


class ErrorDetail(BaseModel):
    message: str
    type: str
    param: str | None = None
    code: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_response(error):
    headers = dict(PRIVATE)
    if error.status == 401:
        headers['WWW-Authenticate'] = 'Bearer'
    if error.status == 429:
        headers['Retry-After'] = str(error.retry_after)
    body = ErrorResponse(error=ErrorDetail(message=error.message, type=error.kind, code=error.code))
    return JSONResponse(body.model_dump(), status_code=error.status, headers=headers)


class Usage(BaseModel):
    model_config = ConfigDict(strict=True)
    prompt_tokens: Count
    completion_tokens: Count
    total_tokens: Count

    @model_validator(mode='after')
    def total(self):
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError('invalid usage')
        return self


class AssistantMessage(BaseModel):
    model_config = ConfigDict(strict=True)
    role: Literal['assistant']
    content: str = Field(max_length=262144)


class Choice(BaseModel):
    model_config = ConfigDict(strict=True)
    index: Annotated[StrictInt, Field(ge=0, le=0)]
    message: AssistantMessage
    finish_reason: Literal['stop', 'length', 'content_filter']


class Completion(BaseModel):
    model_config = ConfigDict(strict=True)
    id: str = Field(pattern=r'^chatcmpl-[A-Za-z0-9_-]{1,100}$')
    object: Literal['chat.completion']
    created: Count
    model: Literal['corvus']
    choices: list[Choice] = Field(min_length=1, max_length=1)
    usage: Usage


class ModelInfo(BaseModel):
    id: Literal['corvus'] = 'corvus'
    object: Literal['model'] = 'model'
    created: int = 0  # Catalog metadata; not a fabricated inference timestamp.
    owned_by: str = 'corvus'


class ModelList(BaseModel):
    object: Literal['list'] = 'list'
    data: list[ModelInfo]


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON member')
            result[k] = v
        return result
    def invalid_constant(value):
        raise ValueError('non-finite JSON number')
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('non-finite JSON number')
        return number
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=finite_float)


def validated_completion(raw, payload):
    result = Completion.model_validate(raw)
    choice = result.choices[0]
    content = choice.message.content
    content.encode('utf-8')
    if raw['choices'][0]['message'].get('tool_calls') or result.usage.completion_tokens > payload['max_tokens']:
        raise ValueError('unsupported upstream result')
    if not content and choice.finish_reason == 'stop':
        raise ValueError('missing visible content')
    if payload['response_format']['type'] == 'json_object':
        try:
            value = strict_json(content)
            if not isinstance(value, dict):
                raise ValueError()
        except (ValueError, RecursionError):
            raise APIError(502, 'invalid_json_output', 'Inference did not return a complete JSON object.', 'server_error') from None
    return result.model_dump()


class Authentication:
    """Authenticate before body buffering, including the private OpenAPI document."""
    def __init__(self, app, *, enabled, key_file):
        self.app, self.enabled, self.key_file = app, enabled, key_file

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        try:
            if not self.enabled or self.key_file is None:
                raise APIError(503, 'api_disabled', 'API is disabled.', 'server_error')
            auth = [v for k, v in scope['headers'] if k.lower() == b'authorization']
            match = re.fullmatch(rb'(?i:Bearer) ([A-Za-z0-9_-]{43,128})', auth[0]) if len(auth) == 1 else None
            if not match or not check_key_file(self.key_file, match[1].decode('ascii')):
                raise APIError(401, 'invalid_api_key', 'Valid Bearer API key required.', 'authentication_error')
            if scope.get('query_string'):
                raise APIError(400, 'query_not_supported', 'Query parameters are unsupported.')
        except KeyConfigurationError:
            return await error_response(APIError(503, 'key_configuration_unavailable', 'API authentication unavailable.', 'server_error'))(scope, receive, send)
        except APIError as error:
            return await error_response(error)(scope, receive, send)
        return await self.app(scope, receive, send)


def create_app(*, enabled=None, key_file=None, generator=stateless_chat_completion,
               tracker=None, request_seconds=90, body_seconds=5, rate_limit=6, clock=monotonic):
    """Explicit test seams; no public request can select credentials or backends."""
    if request_seconds <= 0 or body_seconds <= 0 or type(rate_limit) is not int or rate_limit < 1:
        raise ValueError('invalid API limits')
    if enabled is None:
        enabled = os.getenv('CORVUS_API_ENABLED', 'FALSE') == 'TRUE'
    key_file = key_file if key_file is not None else os.getenv('CORVUS_API_KEY_DIGEST_FILE')
    tracker = tracker if tracker is not None else ForegroundActivityTracker(
        registry_path=os.getenv('CORVUS_API_FOREGROUND_REGISTRY_DIR') or None,
        logical_publisher='api', expected_publishers=('lab', 'production'))
    pool, slot = None, None
    recent = deque()

    @asynccontextmanager
    async def lifespan(app):
        if enabled:
            tracker.start()
        try:
            yield
        finally:
            tracker.close()  # Existing tracker drains active ownership.
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=False)

    api = FastAPI(title='Corvus Text API', version='1.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False,
                  dependencies=[Depends(HTTPBearer(auto_error=False))])
    api.add_middleware(Authentication, enabled=enabled is True, key_file=key_file)

    @api.exception_handler(APIError)
    async def api_error(request, error):
        return error_response(error)

    @api.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(APIError(error.status_code, 'not_found' if error.status_code == 404 else 'request_failed', 'Request not supported.'))

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return error_response(APIError(400, 'invalid_request', 'Invalid request.'))

    @api.exception_handler(Exception)
    async def internal_error(request, error):
        return error_response(APIError(500, 'internal_error', 'API request failed.', 'server_error'))

    errors = {s: {'model': ErrorResponse} for s in [400,401,404,408,413,415,429,499,500,502,503,504]}

    @api.get('/v1/models', response_model=ModelList, responses=errors)
    async def models():
        return JSONResponse(ModelList(data=[ModelInfo()]).model_dump(), headers=PRIVATE)

    async def read_body(request):
        if (request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json'
                or request.headers.get('content-encoding', 'identity').lower() != 'identity'):
            raise APIError(415, 'unsupported_media_type', 'Use uncompressed application/json.')
        lengths = request.headers.getlist('content-length')
        if lengths and (len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal()):
            raise APIError(400, 'invalid_request', 'Invalid request.')
        length = (lengths[0].lstrip('0') or '0') if lengths else None
        if length is not None and (len(length) > 6 or int(length) > MAX_BODY):
            raise APIError(413, 'request_too_large', 'Request body exceeds 128 KiB.')
        data = bytearray()
        try:
            async with asyncio.timeout(body_seconds):
                async for chunk in request.stream():
                    if len(data) + len(chunk) > MAX_BODY:
                        raise APIError(413, 'request_too_large', 'Request body exceeds 128 KiB.')
                    data.extend(chunk)
        except ClientDisconnect:
            raise APIError(499, 'request_cancelled', 'Client disconnected.') from None
        except TimeoutError:
            raise APIError(408, 'body_timeout', 'Request body timed out.') from None
        if length is not None and len(data) != int(length):
            raise APIError(400, 'invalid_request', 'Invalid request body length.')
        return bytes(data)

    @api.post('/v1/chat/completions', response_model=Completion, responses=errors,
              openapi_extra={'requestBody': {'required': True, 'content': {'application/json': {
                  'schema': {'$ref': '#/components/schemas/ChatRequest'}}}}})
    async def chat(request: Request):
        nonlocal slot, pool
        now = clock()
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if slot is not None or len(recent) >= rate_limit:
            error = APIError(429, 'rate_limit_exceeded', 'API is busy; retry later.', 'rate_limit_error')
            if len(recent) >= rate_limit:
                error.retry_after = max(1, math.ceil(60-(now-recent[0])))
            raise error
        owner = object()
        slot = owner
        recent.append(now)
        worker = future = disconnect = None
        stop_polling = asyncio.Event()
        try:
            raw = await read_body(request)
            try:
                parsed = ChatRequest.model_validate(strict_json(raw.decode('utf-8')))
            except (ValueError, UnicodeError, RecursionError):
                raise APIError(400, 'invalid_request', 'Invalid or unsupported request.') from None
            if parsed.model != 'corvus':
                raise APIError(404, 'model_not_found', 'Model not found.')
            payload = parsed.upstream()
            remaining = request_seconds-(clock()-now)
            if remaining <= 0:
                raise APIError(504, 'request_timeout', 'Inference timed out.', 'server_error')
            if pool is None:
                pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corvus-api')
            loop = asyncio.get_running_loop()

            def invoke():
                with tracker.generation():
                    return validated_completion(generator(payload, timeout=remaining), payload)

            def release(unused=None):
                nonlocal slot
                if slot is owner:
                    slot = None

            def settled(real_future):
                # Release only on the actual concurrent worker, never on a cancelled
                # asyncio wrapper. A client deadline cannot cancel a running thread.
                try:
                    loop.call_soon_threadsafe(release)
                except RuntimeError:
                    pass  # Event loop has shut down; no new requests can enter it.

            future = pool.submit(invoke)
            future.add_done_callback(settled)
            worker = asyncio.wrap_future(future)
            worker.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)

            async def watch_disconnect():
                while not stop_polling.is_set():
                    if await request.is_disconnected():
                        return
                    await asyncio.sleep(0.05)

            disconnect = asyncio.create_task(watch_disconnect())
            done, _ = await asyncio.wait({worker, disconnect}, timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
            if worker in done:
                return JSONResponse(worker.result(), headers=PRIVATE)
            if disconnect in done:
                raise APIError(499, 'request_cancelled', 'Client disconnected.')
            raise APIError(504, 'request_timeout', 'Inference timed out.', 'server_error')
        except ModelClientError as error:
            status = {'INPUT_TOO_LONG':400, 'MODEL_TIMEOUT':504, 'MODEL_UNAVAILABLE':503}.get(error.code, 502)
            raise APIError(status, {400:'context_length_exceeded',504:'request_timeout',503:'model_unavailable'}.get(status,'upstream_error'),
                           {400:'Input exceeds the token limit.',504:'Inference timed out.',503:'Inference unavailable.'}.get(status,'Invalid inference response.'),
                           'invalid_request_error' if status == 400 else 'server_error') from None
        except (ValidationError, ValueError, TypeError, KeyError, RecursionError):
            raise APIError(502, 'upstream_error', 'Invalid inference response.', 'server_error') from None
        except APIError:
            raise
        except ClientDisconnect:
            raise APIError(499, 'request_cancelled', 'Client disconnected.') from None
        except Exception:
            raise APIError(500, 'internal_error', 'API request failed.', 'server_error') from None
        finally:
            if disconnect is not None:
                stop_polling.set()
                disconnect.cancel()
                with suppress(asyncio.CancelledError):
                    await disconnect
            if future is None:
                slot = None

    @api.get('/openapi.json', include_in_schema=False)
    async def schema():
        return JSONResponse(api.openapi(), headers=PRIVATE)

    def openapi():
        if api.openapi_schema is None:
            schema = get_openapi(title=api.title, version=api.version, routes=api.routes)
            from pydantic.json_schema import models_json_schema
            _, definitions = models_json_schema([(ChatRequest, 'validation')], ref_template='#/components/schemas/{model}')
            schema.setdefault('components', {}).setdefault('schemas', {}).update(definitions['$defs'])
            api.openapi_schema = schema
        return api.openapi_schema

    api.openapi = openapi
    return api


app = create_app()  # Disabled unless explicitly enabled with independent credentials.
