"""Exact active TTS-image source transform. No live app import or frontend edit."""
import ast
import hashlib
from pathlib import Path
import sys

AUDIO_SHA256 = '807cb1e61894e272eaabf66ffebc13ee64c4f34fb132fda981b2eb6d9404286d'


def patch_audio(source):
    if hashlib.sha256(source.encode()).hexdigest() != AUDIO_SHA256:
        raise ValueError('Expected exact pinned TTS-enabled WebUI 0.6.5 audio source')
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'transcription']
    if len(nodes) != 1:
        raise ValueError('Expected one native transcription route')
    node = nodes[0]
    if (len(node.decorator_list) != 1 or ast.unparse(node.decorator_list[0]) != "router.post('/transcriptions')"
            or ast.unparse(node.args.defaults[-1]) != 'Depends(get_verified_user)'):
        raise ValueError('Expected native verified-user route')
    # Remove UploadFile/File from this signature: Starlette may spool before auth.
    lines = source.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = ['''async def transcription(request: Request, user=Depends(get_verified_user)):
    from open_webui.routers.corvus_stt import transcription as handle
    return await handle(request)
''']
    result = ''.join(lines)
    ast.parse(result)
    return result


if __name__ == '__main__':
    p = Path(sys.argv[1])
    p.write_text(patch_audio(p.read_text()))
