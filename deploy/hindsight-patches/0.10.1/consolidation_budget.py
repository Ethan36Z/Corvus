"""Opt-in exact llama.cpp per-attempt consolidation budget; no fact mutation.

Runs inside the provider attempt's permits AFTER foreground admission. Counting
uses the final provider-wrapped messages and the same server's chat template and
vocabulary. Failure/oversize is durable backpressure, not a failed memory fact.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from urllib.parse import urlsplit, urlunsplit

from hindsight_api.worker.exceptions import DeferOperation

logger = logging.getLogger(__name__)
SCOPES = frozenset(('consolidation', 'consolidation_dedup'))
MIN_COMPLETION = 512


def _defer(reason):
    raise DeferOperation(datetime.now(timezone.utc) + timedelta(seconds=30),
                         'consolidation budget: ' + reason)


def _positive(value, name):
    if isinstance(value, bool):
        raise ValueError(name + ' must be an integer')
    result = int(value)
    if str(result) != str(value) or result <= 0:
        raise ValueError(name + ' must be a positive integer')
    return result


def completion_budget(input_tokens, context, cap, margin):
    """Pure invariant: never steal margin or send an unusably small completion."""
    for value in (input_tokens, context, cap, margin):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError('token budgets must be integers')
    if input_tokens < 0 or min(context, cap, margin) <= 0:
        raise ValueError('invalid token budget')
    allowed = min(cap, context - input_tokens - margin)
    if allowed < MIN_COMPLETION:
        _defer(f'oversized input={input_tokens} context={context} margin={margin}; '
               f'need at least {MIN_COMPLETION} completion tokens')
    return allowed


async def _count_rendered(base_url, body, model, context):
    # Same origin as provider; /v1 is its API suffix, not a separate tokenizer.
    parts = urlsplit(base_url or '')
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.query or parts.fragment:
        raise ValueError('tokenizer requires explicit provider base URL')
    path = parts.path.rstrip('/')
    if not path.endswith('/v1'):
        raise ValueError('expected llama.cpp /v1 base URL')
    origin = urlunsplit((parts.scheme, parts.netloc, path[:-3], '', ''))
    import aiohttp
    # No generation requests/retries; counting has one bounded total horizon.
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), trust_env=False) as session:
        async def read(method, suffix, payload=None):
            async with session.request(method, origin + suffix, json=payload) as response:
                response.raise_for_status()
                return await response.json()
        props = await read('GET', '/props')
        if props.get('model_alias') != model or props['default_generation_settings']['n_ctx'] != context:
            raise ValueError('tokenizer model/context identity mismatch')
        rendered = await read('POST', '/apply-template', body)
        prompt = rendered.get('prompt')
        if not isinstance(prompt, str) or not prompt:
            raise ValueError('invalid rendered chat prompt')
        tokenized = await read('POST', '/tokenize',
                               {'content': prompt, 'add_special': True, 'parse_special': True})
        tokens = tokenized.get('tokens')
        if not isinstance(tokens, list) or any(type(t) is not int for t in tokens):
            raise ValueError('invalid tokenizer result')
        return len(tokens)


async def enforce_consolidation_budget(provider, scope, params):
    """Bound the actual SDK request, including extra-body overrides, every attempt.

    Unconfigured/non-consolidation calls retain vanilla behavior. Configured
    unknown/incompatible counting defers without consuming provider retry budget.
    """
    enabled = os.getenv('CORVUS_CONSOLIDATION_CONTEXT_LIMIT')
    if scope not in SCOPES or enabled is None:
        return
    try:
        context = _positive(enabled, 'context')
        cap = _positive(os.getenv('HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS', '1024'), 'cap')
        margin = _positive(os.getenv('CORVUS_CONSOLIDATION_SAFETY_MARGIN_TOKENS', '256'), 'margin')
        if provider.provider not in ('openai', 'llamacpp'):
            raise ValueError('exact budget supported only for llama.cpp OpenAI-compatible transport')
        extra = params.get('extra_body', {})
        if not isinstance(extra, dict) or set(extra) & {'model', 'messages', 'max_tokens', 'max_completion_tokens'}:
            raise ValueError('unsafe extra_body request/token override')
        body = {**{k: v for k, v in params.items() if k != 'extra_body'}, **extra}
        # Consolidation-only reasoning policy; never touch foreground or retain.
        body['reasoning_effort'] = 'none'
        template = dict(body.get('chat_template_kwargs') or {})
        template['enable_thinking'] = False
        body['chat_template_kwargs'] = template
        key = provider._max_tokens_param_name()
        requested = body.get(key)
        if requested is not None:
            cap = min(cap, _positive(requested, 'requested completion cap'))
        async with asyncio.timeout(5):
            count = await _count_rendered(provider.base_url, body, provider.model, context)
        allowed = completion_budget(count, context, cap, margin)
        # Both max fields must agree if a caller supplied the alternate spelling.
        for alternate in ('max_tokens', 'max_completion_tokens'):
            if alternate != key:
                params.pop(alternate, None)
        params[key] = allowed
        params['reasoning_effort'] = 'none'
        params['extra_body'] = {**extra, 'chat_template_kwargs': template}
        # Counting adds a short interval: recheck foreground immediately before
        # provider send, while still holding the existing per-attempt permits.
        from hindsight_api.engine.foreground_admission import check_foreground_admission
        check_foreground_admission()
        logger.info('[CONSOLIDATION_BUDGET] scope=%s input_tokens=%d completion_tokens=%d '
                    'safety_margin=%d context_limit=%d total_reserved=%d request_parameter=%s '
                    'reasoning=none thinking=false', scope, count, allowed, margin, context,
                    count + allowed + margin, key)
    except DeferOperation:
        raise
    except Exception as error:
        logger.warning('Consolidation budget preflight unavailable: %s: %s', type(error).__name__, error)
        _defer('cannot prove safe input/output budget')
