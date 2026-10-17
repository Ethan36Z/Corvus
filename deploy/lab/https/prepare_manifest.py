"""Build-time Lab manifest patch; fail on any unexpected UI-2.1 backend source."""

import ast
import hashlib
import json
from pathlib import Path
import sys


BASE_MAIN_SHA256 = "ef004613b0c228ca0a55d08616aeba76adadb1c1f53713f05b20a492453701c2"


def prepare(source, manifest):
    if hashlib.sha256(source.encode()).hexdigest() != BASE_MAIN_SHA256:
        raise ValueError("Expected unchanged pinned Lab UI-2.1 main.py")
    tree = ast.parse(source)
    matches = [node for node in tree.body
               if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_manifest_json"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one manifest handler")
    node = matches[0]
    replacement = (
        "async def get_manifest_json():\n"
        f"    return JSONResponse(content={manifest!r}, media_type='application/manifest+json')\n"
    )
    lines = source.splitlines(keepends=True)
    # Retain the route decorator and all other source byte-for-byte.
    result = "".join(lines[:node.lineno - 1]) + replacement + "".join(lines[node.end_lineno:])
    ast.parse(result)
    return result


if __name__ == "__main__":
    path = Path(sys.argv[1])
    manifest = json.loads(Path(__file__).with_name("manifest.json").read_text())
    path.write_text(prepare(path.read_text(), manifest))
