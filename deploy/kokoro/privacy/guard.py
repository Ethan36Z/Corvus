"""Content-free process logging for the pinned Kokoro service (Python 3.10).

No caller-supplied message, exception, pathname, header or extra field is emitted.
The private descriptor is never exposed to the synthesis libraries as a stream.
"""
import asyncio
import json
import logging
import os
import sys
import threading
import time
import warnings

_OUTPUT = None
_LEVELS = {'TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'}
_COMPONENTS = {
    'api.src.routers.openai_compatible': 'speech',
    'api.src.services.tts_service': 'tts',
    'api.src.services.text_processing.text_processor': 'text',
    'api.src.inference.kokoro_v1': 'model',
    'api.src.services.audio': 'audio',
    'api.src.services.streaming_audio_writer': 'codec',
    'uvicorn.error': 'server', 'uvicorn.access': 'http',
}


def emit(event, level='INFO', component='runtime', line=0, status=0, elapsed_ms=0):
    """Only fixed enums and bounded numbers may cross the output boundary."""
    if _OUTPUT is None:
        raise RuntimeError('privacy boundary not installed')
    record = {
        'event': event if event in {'log', 'request', 'cancelled', 'unhandled',
                                  'warning', 'startup', 'download', 'exit'} else 'log',
        'level': level if level in _LEVELS else 'ERROR',
        'component': component if component in set(_COMPONENTS.values()) else 'runtime',
        'line': min(max(line, 0), 10000) if type(line) is int else 0,
        'status': status if type(status) is int and 0 <= status <= 599 else 0,
        'elapsed_ms': min(max(elapsed_ms, 0), 86400000) if type(elapsed_ms) is int else 0,
    }
    # One short atomic write, no fallback to unsanitized traceback or message.
    os.write(_OUTPUT, (json.dumps(record, separators=(',', ':')) + '\n').encode('ascii'))


def contain_output():
    """Process-wide, before library imports; includes native fd writes/children."""
    global _OUTPUT
    if _OUTPUT is not None:
        return
    _OUTPUT = os.dup(2)
    os.set_inheritable(_OUTPUT, False)
    null = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, 1)
        os.dup2(null, 2)
    finally:
        os.close(null)
    sys.excepthook = lambda *_: emit('unhandled', 'CRITICAL')
    sys.unraisablehook = lambda *_: emit('unhandled', 'ERROR')
    threading.excepthook = lambda *_: emit('unhandled', 'ERROR')
    warnings.showwarning = lambda *a, **kw: emit('warning', 'WARNING')


class MetadataHandler(logging.Handler):
    def emit(self, record):
        # Deliberately never call getMessage(), format(), or inspect exc_info.
        emit('log', record.levelname, _COMPONENTS.get(record.name, 'runtime'), record.lineno)


def configure_logging():
    from loguru import logger
    logger.remove()

    def sink(message):
        record = message.record
        emit('log', record['level'].name,
             _COMPONENTS.get(record['name'], 'runtime'), record['line'])

    logger.add(sink, level='TRACE', format='{level}', backtrace=False,
               diagnose=False, catch=False)
    root = logging.getLogger()
    root.handlers[:] = [MetadataHandler()]
    root.setLevel(logging.DEBUG)
    for item in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(item, logging.Logger):
            item.handlers.clear()
            item.propagate = True
            item.disabled = False
    # Future custom stream handlers still write only to contained fd 1/2.


class Outcomes:
    """ASGI pass-through: log bounded outcome metadata, never request data."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        start = time.monotonic()
        status = 0
        event = 'request'
        level = 'INFO'

        async def observe(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)

        try:
            await self.app(scope, receive, observe)
        except asyncio.CancelledError:
            event, level = 'cancelled', 'WARNING'
            raise
        except BaseException:
            event, level = 'unhandled', 'ERROR'
            raise
        finally:
            if status >= 500:
                level = 'ERROR'
            elif status >= 400 and level == 'INFO':
                level = 'WARNING'
            emit(event, level, 'http', status=status,
                 elapsed_ms=int((time.monotonic() - start) * 1000))
