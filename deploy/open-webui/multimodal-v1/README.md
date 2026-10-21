# Existing Multimodal v1 frontend source checkpoint

This saves the exact cumulative native source integration used by the deployed
chat-recovery image. It is source, not compiled JS, source maps, node_modules,
Pyodide, user data, credentials or a new build system. Earlier feature commits
remain authoritative for each implementation; this patch closes their final
full-Svelte-build packaging gap. Do not reapply the older incremental JS packager.

## Reuse the original build process

1. Use the original Open WebUI v0.6.5 archive and lockfile pinned in
   `source-lock.json`; verify their SHA256 values. Do not substitute current upstream.
2. Run the existing `branding/verify_branding.py --prepare-source SOURCE
   --archive ARCHIVE --arena-ui2`. This applies the existing branding and Arena
   patches. `source_checks(..., arena_ui2=True)` verified the retained base before
   creating this checkpoint (117 files). No upstream source is vendored here.
3. Check every `files.*.before` hash, then use ordinary `git apply --check --whitespace=error` and
   `git apply` on `frontend.patch` from that prepared source directory. It changes
   exactly seven native files. Copy the three existing helpers from the repository
   paths in `copy_existing_helpers`; verify all ten `after` hashes. This patch is
   an alternative cumulative frontend assembly; do not stack the earlier frontend
   generators on top of it.
4. Copy the existing branding assets and retain the pinned Pyodide assets as in
   the existing R7 `package/prepare.py` and original image build. Use the original
   lockfile with retained dependencies and Node 22 image in `source-lock.json`.
   Run the existing `svelte-kit sync` and `vite build`; run the existing
   `tests/test_webui_vision_frontend.mjs` with its documented fixture environment.
   No minifier/string replacement substitutes for compiling the Svelte components.
5. Reuse the existing frontend-only image recipe: the retained wired WebUI image
   is the base; remove only its `/app/build` image layer contents and COPY the full
   new static `build/` there. Backend STT/TTS/Vision routes, credentials, Pipe/model
   settings and deployment volumes are separate and must be preserved by the
   existing scoped deployment process. This checkpoint does not deploy anything.

The existing normal build/checks passed for this exact source on 2026-10-20.
During local closure the cumulative patch was reapplied in an isolated directory
and every resulting source hash checked. No dependency install, frontend rebuild,
image build or inference is part of closure. Runtime asset IDs are local artifact
identities, not promises that a registry serves those IDs. Retain the existing
pinned base images and cache separately; do not commit those binary artifacts.

## Related existing commits, not merged by this checkpoint

- STT activation, auth and owner repair: `6dfc522`, `6a2a5eb`, `dc46ab5`.
- Browser WAV / streaming WebM fix: `83ca1d3`, `953d7c8`.
- Persistent STT sources/restart policies: `75e3cf9` on its own branch.
- Kokoro logging derivative: `7c0b5d0` on its own branch.
- Vision single store / 20 MiB / preview / next-turn recovery:
  `da3d9c3`, `4f138cf`, `4845db5`, `4d5b584`, `e5afa68`, `a7558fd`.
- Server-only Pillow inference resize: `98ae271`; no frontend payload changes.

Secrets/admission files, user ownership records, private Compose packets and
WebUI user data remain outside Git. Reconstruct their settings through the
existing authenticated provisioning/backup procedures; never copy them from a
chat database into a source checkpoint.
