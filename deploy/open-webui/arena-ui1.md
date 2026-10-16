# Memory Arena UI-1 — prepared Lab image

UI-1 adds the Memory A/B toggle, single Arena chat transport, structured event,
and a persisted read-only comparison panel. Voting and Action relay are deferred.
No Corvus backend, normal chat endpoint, H1 lifecycle, or RAG implementation is
changed. This revision is prepared for review and is not deployed.

## Pinned build

The original OW2d branding patch and Production Dockerfile/compose files remain
unchanged. `branding/patches/arena-ui1.patch` applies after that branding patch
to upstream v0.6.5 commit `07d8460126a686de9a99e2662d06106e22c3f6b6`.
`branding/arena-ui1.lock.json` records the base patch, overlay hash, and every
before/after source hash. The existing verifier accepts `--arena-ui1` to verify
and apply both layers. The shared Pipe checksum now covers the extended Pipe;
its Arena valve defaults false and its normal path is covered by regressions.

Final candidate (built, not deployed): `corvus-open-webui:0.6.5-arena-ui1.2`.
Verified image identity:
`sha256:ae941e36d670a5462edb9566617a027e3c15467c4601af0ad8c43a74822c2cf7`.
The development `ui1.1` tag was rebuilt previously; this candidate uses a new tag.
Record/verify this digest at deployment and acceptance.

`Dockerfile.arena-ui1` builds only
`corvus-open-webui:0.6.5-arena-ui1.2`, with immutable runtime/Node 22 image pins.
`deploy/lab/compose.arena-ui1.yml` is a prepared override for Lab's existing
`compose.webui.yml`; the active compose file and running containers are unchanged.
Do not use this revision for Production. Deployment and Function import require
a later authorized step; no source is patched inside running containers.

## Behavior

`Chat.svelte` owns the in-memory toggle, initially false. Both the fresh-chat
placeholder and existing-chat input bind to it. Only an opted-in new submission
captures the flag and adds `metadata.corvus_arena: true`. Saved panels, retries,
continuations, and reloaded history cannot enable the flag. OFF payloads remain
unchanged. The metadata normalizer copies only this literal boolean true into
its authenticated metadata, never arbitrary client identity or other fields.

The Pipe requires `ARENA_ENABLED=true` and its admin chat URL to be exactly
`http://127.0.0.1:18096/api/chat` before an opted-in POST to `/api/arena/chat`.
The Arena request contains only the stable session ID and current text. Normal
requests retain their existing URL, payload, web-mode valve, and transport policy.
There are no retries or fallback requests. Only confirmed `main.reply` is
returned as assistant content. One `corvus:arena:v1` event attempt carries the
whitelisted display payload through the injected emitter. Construction errors,
emitter errors/cancellation, and a one-second emitter timeout preserve that reply.

The UI validates the event and its chat/assistant identity, requiring the
requested-turn marker. It attaches `corvus_arena` to that assistant message,
rejects duplicate/reassigned trials, and attaches the panel locally. If the target
assistant is not complete, the Arena event performs no history write and schedules
no retry. Normal completion saves the finished reply and attached panel together.
An event arriving after completion saves through the same queue, provided the
reply is nonempty. This avoids any Arena-originated placeholder snapshot racing
with upstream server completion; upstream backend/socket/title writers are unchanged.
All full-history writes use one Chat-owned per-chat queue from component start,
including writes delegated by Messages.svelte. Each save captures an immutable
snapshot of the active chat before enqueueing; navigation cannot retarget it,
and responses for an inactive chat cannot replace active chat state. Failed
saves release the queue without retries. Completion callbacks preserve attached
Arena fields. Assistant edits and Save as Copy strip the Arena association;
ratings preserve it and the separate evaluation trial remains untouched. Panels restore from
saved history; the toggle does not. Display metadata never enters provider
messages or Corvus canonical memory.

The panel renders only the Hindsight candidate through the existing content
renderer with editing/save and floating actions disabled. Evidence is escaped
plain text in a collapsed native details element using existing layout styles.
It shows retrieval/generation timing, status, namespaces, and fairness, with
provider/empty-evidence/evaluation-unavailable states. There are no vote controls.

## Verification

Prepare a new temporary source directory using the checksum-verified archive:

```sh
python3 -B deploy/open-webui/branding/verify_branding.py --arena-ui1 \
  --prepare-source /tmp/corvus-ui1-source --archive /path/to/pinned-upstream.tar.gz
CORVUS_OW2D_ARCHIVE=/path/to/pinned-upstream.tar.gz \
  .venv/bin/python -B -m unittest discover -s tests -p 'test_open_webui*.py' -v
```

Install dependencies from the unchanged lockfile using the pinned Node 22 builder
(`CYPRESS_INSTALL_BINARY=0 npm ci --no-audit --no-fund`). Run
`node tests/frontend/memory-arena-ui1.mjs /tmp/corvus-ui1-source` against that tree.
The frontend tests exercise real patched helper functions and compiled Svelte
markup; candidate rendering is stubbed in SSR state tests. The production Vite
build additionally compiles the actual content renderer and all integration code.
Run `svelte-kit sync`, strict `tsc --noEmit` on `src/lib/corvus-arena.ts`, the
direct Vite build (without the upstream Pyodide fetcher), and `git diff --check`.

All test API calls are mocked. A full image build runs source/image verification
without starting Open WebUI or making Corvus/Hindsight/model requests.

Known delivery limit: if a browser leaves the chat or refreshes before receiving
and saving the custom event, the panel cannot be recovered from the current
backend API. In particular, leaving or refreshing after local attachment but
before completion/save may lose the panel; this is accepted v0 behavior. The
Arena event must not persist an older placeholder over a server-completed reply.
A requested completed turn without a saved payload shows comparison unavailable.
History-save errors leave the candidate visible in memory and report a save
failure; no chat request or event is retried. Real browser/service integration
remains for a separately authorized Lab smoke test.
