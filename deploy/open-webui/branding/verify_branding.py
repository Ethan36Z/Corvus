"""Fail-closed verification/preparation for the pinned Corvus distribution.

Default: check repository artifacts. --source checks the patched upstream tree.
--image-root checks a built image filesystem without starting the application.
--prepare-source downloads/verifies/extracts/patches into a new empty directory.
All checks use the standard library; no API calls or Corvus imports.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import urllib.request


HERE = Path(__file__).resolve().parent
BRAND = re.compile(r"open[ -]?web[ -]?ui|openwebui", re.I)
BARE_PRODUCT = re.compile(r"(?<![A-Za-z0-9_.-])WebUI(?![A-Za-z0-9_.-])")
PROMOTION = re.compile(r"https?://(?:[^\s/'\"]*openwebui\.com|github\.com/open-webui|twitter\.com/OpenWebUI|discord\.gg/5rJgQTnV4s)", re.I)
FORMATTER_INPUTS = (
    "OW1 does not support Open WebUI search, media, or tool features.",
    "Required stable unique ID for this Open WebUI installation.",
)
ORIGIN_FILES = {
    "src/routes/(app)/admin/functions/create/+page.svelte",
    "src/routes/(app)/workspace/models/create/+page.svelte",
    "src/routes/(app)/workspace/prompts/create/+page.svelte",
    "src/routes/(app)/workspace/tools/create/+page.svelte",
}
BACKEND_FILES = {
    "backend/open_webui/config.py", "backend/open_webui/env.py",
    "backend/open_webui/main.py", "backend/open_webui/routers/audio.py",
    "backend/open_webui/routers/ollama.py", "backend/open_webui/routers/openai.py",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lock_data():
    return json.loads((HERE / "upstream.lock.json").read_text())


def patch_paths():
    return re.findall(r"^\+\+\+ b/(.+)$", (HERE / "patches/ow2d-corvus.patch").read_text(), re.M)


def artifact_checks():
    lock = lock_data()
    require(lock["upstream"]["commit"] == "07d8460126a686de9a99e2662d06106e22c3f6b6", "Unexpected upstream commit")
    require(lock["upstream"]["version"] == "0.6.5", "Unexpected version")
    require(lock["runtime_image"].endswith("@sha256:fe7a6870ec6b2fd540c0f2007e6aa812dc4bf04a2d0a305bb344eeb10de0a7b7"), "Unexpected runtime image")
    dockerfile = (HERE.parent / "Dockerfile.corvus").read_text()
    require(lock["runtime_image"] in dockerfile and lock["builder_image"] in dockerfile, "Dockerfile image pin mismatch")
    require(sha(HERE / "patches/ow2d-corvus.patch") == lock["patch_sha256"], "Patch checksum mismatch")
    require(set(patch_paths()) == set(lock["patched_files"]), "Patch file scope mismatch")
    for path in patch_paths():
        require(path.startswith("src/") or path in BACKEND_FILES or path in {"static/opensearch.xml", "static/static/site.webmanifest"}, f"Unexpected patch target: {path}")
    for name, metadata in lock["assets"].items():
        require(sha(HERE / "assets" / name) == metadata["sha256"], f"Asset checksum mismatch: {name}")
        if name.endswith(".png"):
            content = (HERE / "assets" / name).read_bytes()
            require(content.startswith(b"\x89PNG\r\n\x1a\n"), f"Not a PNG: {name}")
            require(list(struct.unpack(">II", content[16:24])) == metadata["size"], f"Wrong dimensions: {name}")
    notices = (HERE / "THIRD_PARTY_NOTICES.txt").read_text()
    require(lock["license_text"] in notices, "Upstream license was not retained intact")
    require("CC-BY 4.0" in notices and "Twemoji" in notices, "Emoji attribution missing")
    require(sha(HERE.parent / "corvus_pipe.py") == lock["corvus_pipe_sha256"], "Corvus Pipe changed")
    return lock


def scan_text(path, text):
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if not (BRAND.search(line) or BARE_PRODUCT.search(line) or PROMOTION.search(line)):
            continue
        # Non-rendered origin validation stays exact; removing/renaming it would
        # change trust boundaries. It is never an application label or link.
        if path in ORIGIN_FILES and "!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:" in line:
            continue
        # The only retained frontend branding literals are exact input keys for
        # the immutable Pipe's presentation formatter. Not used for chat text.
        if path == "src/lib/corvus-branding.ts" and any(f".replace('{key}'," in line for key in FORMATTER_INPUTS):
            continue
        findings.append(f"{path}:{number}: application branding remains")
    return findings


def source_checks(root):
    lock = artifact_checks()
    root = Path(root)
    for path, metadata in lock["patched_files"].items():
        require(sha(root / path) == metadata["after"], f"Patched source checksum mismatch: {path}")
    require(sha(root / "package-lock.json") == lock["upstream"]["package_lock_sha256"], "npm lock changed")
    require((root / "LICENSE").read_text() == lock["license_text"], "Source license changed")
    findings = []
    for path in (root / "src").rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".js", ".svelte", ".html", ".json"}:
            findings += scan_text(path.relative_to(root).as_posix(), path.read_text())
    for p in ["static/opensearch.xml", "static/static/site.webmanifest"]:
        findings += scan_text(p, (root / p).read_text())
    require(not findings, "\n".join(findings))
    layout = (root / "src/routes/(app)/+layout.svelte").read_text()
    require("checkForVersionUpdates" not in layout and "<ChangelogModal" not in layout and "<UpdateInfoToast" not in layout, "Automatic update/release UI remains")
    require(lock["license_text"].strip() in (root / "src/lib/components/chat/Settings/About.svelte").read_text(), "About license missing")
    for path in (root / "src").rglob("*.svelte"):
        require("getVersionUpdates" not in path.read_text(), f"Visible update check remains: {path}")
    return {"patched_files": len(lock["patched_files"]), "application_branding_findings": 0}


def prepare_source(destination, archive_path=None):
    lock = artifact_checks()
    destination = Path(destination)
    require(not destination.exists() or not any(destination.iterdir()), "Source destination must be empty")
    with tempfile.TemporaryDirectory(prefix="corvus-branding-") as temporary:
        archive = Path(archive_path) if archive_path else Path(temporary) / "upstream.tar.gz"
        if not archive_path:
            with urllib.request.urlopen(lock["upstream"]["archive_url"], timeout=120) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
        require(sha(archive) == lock["upstream"]["archive_sha256"], "Upstream archive checksum mismatch")
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                parts = PurePosixPath(member.name).parts
                require(not member.name.startswith("/") and ".." not in parts, "Unsafe archive path")
                if len(parts) < 2:
                    continue
                target = destination.joinpath(*parts[1:])
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.extractfile(member).read())
                else:
                    raise ValueError(f"Unexpected archive link/device: {member.name}")
        for path, metadata in lock["patched_files"].items():
            require((sha(destination / path) if (destination / path).exists() else None) == metadata["before"], f"Unexpected original source: {path}")
        patch = str(HERE / "patches/ow2d-corvus.patch")
        for args in [["--check"], []]:
            subprocess.run(["git", "apply", "--whitespace=error", *args, patch], cwd=destination, check=True)
    return source_checks(destination)


def image_checks(root):
    lock = lock_data()
    root = Path(root)
    for path, metadata in lock["patched_files"].items():
        if path.startswith("backend/"):
            require(sha(root / "app" / path) == metadata["after"], f"Runtime source changed: {path}")
    for directory in [root / "app/build/static", root / "app/backend/open_webui/static"]:
        for name, metadata in lock["assets"].items():
            require(sha(directory / name) == metadata["sha256"], f"Missing/old runtime asset: {directory.name}/{name}")
    require(sha(root / "app/build/favicon.png") == lock["assets"]["favicon.png"]["sha256"], "Root favicon remains")
    require(sha(root / "app/backend/open_webui/static/swagger-ui/favicon.png") == lock["assets"]["favicon.png"]["sha256"], "Swagger favicon remains")
    for directory in [root / "app/build/static", root / "app/backend/open_webui/static"]:
        manifest = json.loads((directory / "site.webmanifest").read_text())
        require(manifest["name"] == manifest["short_name"] == "Corvus", "Static PWA branding remains")
    require(json.loads((root / "app/package.json").read_text())["version"] == "0.6.5", "Runtime version changed")
    require(lock["license_text"] in (root / "usr/share/doc/corvus/THIRD_PARTY_NOTICES.txt").read_text(), "Image license missing")
    index = (root / "app/build/index.html").read_text()
    require("<title>Corvus</title>" in index and not BRAND.search(index), "Built shell branding remains")
    # Compiled bundles retain non-rendered origins and formatter input keys.
    # Remove only those exact known literals before scanning generated UI assets.
    for path in (root / "app/build").rglob("*"):
        if path.is_file() and path.suffix in {".js", ".html", ".json", ".webmanifest", ".xml"} and "pyodide" not in path.parts:
            text = path.read_text()
            for key in FORMATTER_INPUTS:
                text = text.replace(key, "")
            text = text.replace("https://openwebui.com", "").replace("https://www.openwebui.com", "")
            require(not BRAND.search(text) and not BARE_PRODUCT.search(text) and not PROMOTION.search(text), f"Built application branding remains: {path}")
    return {"runtime_assets_verified": len(lock["assets"]), "application_branding_findings": 0, "version": "0.6.5"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--source", type=Path)
    modes.add_argument("--image-root", type=Path)
    modes.add_argument("--prepare-source", type=Path)
    parser.add_argument("--archive", type=Path, help="Use a local checksum-verified archive instead of downloading")
    args = parser.parse_args()
    try:
        if args.prepare_source:
            result = prepare_source(args.prepare_source, args.archive)
        elif args.source:
            result = source_checks(args.source)
        elif args.image_root:
            result = image_checks(args.image_root)
        else:
            lock = artifact_checks()
            result = {"version": lock["upstream"]["version"], "patch_targets": len(patch_paths()), "assets": len(lock["assets"])}
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Branding verification FAILED: {error}\n")
    print(json.dumps({"status": "PASS", **result}, indent=2))


if __name__ == "__main__":
    main()
