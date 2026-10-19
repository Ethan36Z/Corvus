"""Exact-source build patch; retain native route/auth and existing UI controls."""

import ast
import hashlib
from pathlib import Path
import sys


AUDIO_SHA256 = "1626d6fd494097836018f72bc8579a72544d8012ffdfe85ae32c20a501a8e3ba"
FRONTEND_SHA256 = "3238bda1781a34de6474b054c03f55927e51e9128988218d73c657e29fa23ba5"
FRONTEND_PATH = "_app/immutable/chunks/DN99fuHl.js"
DEBUG_CALL = 'console.debug("Prepared message content for TTS",kt),'


def patch_audio(source):
    if hashlib.sha256(source.encode()).hexdigest() != AUDIO_SHA256:
        raise ValueError("Expected exact pinned Lab 0.6.5 audio.py")
    lines = source.splitlines(keepends=True)
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, ast.AsyncFunctionDef) and n.name in {"speech", "get_voices"}]
    if {n.name for n in nodes} != {"speech", "get_voices"} or len(nodes) != 2:
        raise ValueError("Expected two native authenticated audio routes")
    for node in sorted(nodes, key=lambda n: n.lineno, reverse=True):
        target = "speech" if node.name == "speech" else "voices"
        # Signature and decorators, including Depends(get_verified_user), stay exact.
        start = node.body[0].lineno - 1
        lines[start:node.end_lineno] = [
            f"    from open_webui.routers.corvus_tts import {target} as handle\n",
            "    return await handle(request)\n",
        ]
    result = "".join(lines)
    cache = ('SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"\n'
             'SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)\n')
    if result.count(cache) != 1:
        raise ValueError("Unexpected speech cache initialization")
    result = result.replace(cache, "# Lab TTS has no speech cache.\n")
    ast.parse(result)
    return result


def patch_frontend(source):
    if hashlib.sha256(source.encode()).hexdigest() != FRONTEND_SHA256 or source.count(DEBUG_CALL) != 1:
        raise ValueError("Expected exact pinned UI-2.1 TTS debug statement")
    return source.replace(DEBUG_CALL, "")


if __name__ == "__main__":
    audio = Path(sys.argv[1])
    frontend = Path(sys.argv[2]) / FRONTEND_PATH
    # Verify both before writing either file. No runtime data is opened.
    patched_audio = patch_audio(audio.read_text())
    patched_frontend = patch_frontend(frontend.read_text())
    audio.write_text(patched_audio)
    frontend.write_text(patched_frontend)
