# Stages OW1 / OW2a: Corvus Function Pipe contract

Status: implementation and offline contract tests only. Open WebUI has not been
installed or deployed. The existing Corvus UI, API, runtime, and production
services are unchanged. Hindsight remains outside scope. OW2a adds only an admin
endpoint valve, offline tests, and an isolated-instance plan; no instance has
been started.

## Version and authority

Open WebUI is pinned to **v0.6.5** in `compose.ow1.yml`:
`ghcr.io/open-webui/open-webui:v0.6.5`. Do not replace it with `main`, `latest`, or
another version without reviewing the adapter contract. The Function header's
`required_open_webui_version` declares a minimum; the exact deployment pin is the
image tag. A registry digest has not been resolved or pulled during OW1.

The only conversation path is:

```text
Open WebUI v0.6.5 -> Corvus Function Pipe
    -> POST <admin CORVUS_CHAT_URL> -> Corvus /api/chat -> process_turn()
```

The default remains exactly `http://127.0.0.1:8096/api/chat` (production).
Isolated live acceptance must explicitly use `http://127.0.0.1:18096/api/chat`.

Corvus remains responsible for context, personality, retrieval, web mode,
generation, and canonical persistence. Open WebUI receives only the reply text.
There is no OpenAI/Ollama connection to llama.cpp, history replay into Corvus,
Hindsight connection, or alternate runtime. Open WebUI stores its own display
history; that history does not override Corvus memory.

The adapter uses `httpx` and Pydantic already present in the v0.6.5 dependency
graph (HTTPX through OpenAI). It imports no Corvus modules and requires no new
Corvus package installation.

## Identity

Admin valve `INSTANCE_ID` is required, with no shared default. Assign a stable,
unique value per Open WebUI installation and preserve it with that installation's
database backups. Treat it as a namespace, not a credential.

Identity comes from the authenticated injected `__user__["id"]` and injected
`__chat_id__`, or retained metadata `chat_id`. Conflicting chat/user metadata is
rejected. IDs must be nonempty strings without surrounding whitespace. The chat
ID must be a canonical lowercase UUID representing a saved v0.6.5 chat; missing,
`local`, `local:*`, and other temporary IDs fail before any POST. A UUID is a
format check, not an independent database ownership check: Open WebUI must enforce
its own authenticated chat access.

The exact mapping is:

```python
identity = json.dumps(
    [INSTANCE_ID, user_id, chat_id],
    ensure_ascii=False,
    separators=(",", ":"),
).encode("utf-8")
session_id = "ow1:" + hashlib.sha256(identity).hexdigest()
```

JSON tuple encoding avoids delimiter collisions. The mapping survives socket
reconnects and Pipe restarts. Browser/socket `session_id`, message IDs, email,
display name, and model name never participate. Changing any identity component
creates a different Corvus session. No mapping table or memory migration is added.

This namespace prevents session collisions; it does not introduce tenant isolation
into Corvus's existing memory/retrieval policy. OW1 is for the existing private
trusted-user environment, not a new multi-tenant service.

## Accepted turns and valves

An ordinary turn must end in a nonempty user message with string content. Earlier
system/user/assistant messages are checked for unsupported content but are never
forwarded. The payload contains exactly:

```json
{"session_id": "ow1:<sha256>", "message": "current user text", "web_mode": "auto"}
```

Only the current text is sent, without adapter trimming or concatenation. Corvus's
existing API strips surrounding whitespace. UI prompts, history, generation
parameters, client web mode, and user valves cannot override the Corvus runtime.

Admin valves:

| Valve | Default | Contract |
| --- | --- | --- |
| `CORVUS_CHAT_URL` | `http://127.0.0.1:8096/api/chat` | Admin-only; literal HTTP loopback chat URL with a valid port. Set to `http://127.0.0.1:18096/api/chat` for acceptance. |
| `INSTANCE_ID` | empty | Must be set before any conversation POST. |
| `WEB_MODE` | `auto` | `off`, `on`, or `auto`, forwarded to Corvus only. |
| `TIMEOUT_SECONDS` | `300` | HTTPX I/O timeout, 1–600 seconds; connect timeout is 5 seconds. |

There are no user valves. `CORVUS_CHAT_URL` is selected only from the admin
`Pipe.Valves`, never from body fields, parameters, user input, user valves, or
request metadata. Its exact allowed form is
`http://127.0.0.1:<port>/api/chat`, where the port is 1–65535 in ASCII decimal
without leading zeros. Validation happens on valve loading and again before
conversation I/O; invalid configuration never falls back to production.
Remote hosts, DNS names (including `localhost`), other IP literals, HTTPS,
credentials, query strings, fragments, alternate/encoded paths, whitespace,
malformed ports, and other destinations are rejected without URL normalization.
Client-facing errors from `pipe()` never echo the rejected URL or credentials.
This is a destination restriction, not authentication of the process listening
on a local port. Corvus web mode is distinct from Open WebUI web search, which is
unsupported.

Rejected before Corvus I/O:

- Temporary/local chats and missing or conflicting identity.
- Files, attachments, image/audio/video input, multipart content (even text-only
  content arrays), media output, and tool/function messages or selections.
- Enabled Open WebUI web search, image generation, code interpreter, or other
  feature flags, including flags retained by middleware in metadata.
- Multiple responses, explicit regenerate/branch/continue/operation markers, and
  assistant-final requests such as continuation.

Task-marked calls return empty text locally before identity validation or I/O.
This includes title, tags, query, autocomplete, emoji, function calling, model
aggregation, and unknown future tasks. Both injected `__task__`/`__task_body__`
and body/metadata task fields are checked. No task prompt enters Corvus memory.
The deployment settings also disable title, tags, and autocomplete generation.
Automatic task suppression may leave default titles and no generated tags.

## Results and uncertain outcomes

Each accepted call issues exactly one non-streaming Corvus POST. HTTP transport
retries, redirects, and environment proxy routing are disabled. Open WebUI can
request streaming; v0.6.5 wraps the returned string after Corvus finishes, so OW1
does not stream tokens from Corvus or provide a Corvus cancellation endpoint.

A reply requires HTTP 200, the matching session ID, a nonempty string reply,
overall `OK` or `DEGRADED`, model `OK`, and persistence `NORMAL`. Retrieval/dense
degradation with a confirmed model reply is allowed; detailed diagnostics remain
in Corvus. Failed/unconfirmed persistence and model failures return a fixed error.
The adapter never includes backend error bodies, error fields, retrieved memories,
exception messages, or diagnostic details in client errors.

Timeouts, connection failures, malformed responses, and unsuccessful responses
produce fixed messages explaining that the turn may already have been saved.
The adapter never retries. A caller disconnect/stop can also occur after Corvus
has started or saved the turn. Inspect Corvus's canonical session before deciding
whether to send again. OW1 has no idempotency keys, deduplication, regenerate,
history reconciliation, or branch support. Explicit unsupported markers fail
closed, but v0.6.5's normal regenerate/edit/branch UI can emit an ordinary chat
payload without an operation marker. A stateless Pipe cannot distinguish that
payload from a new turn. Do not use those controls, model comparison/aggregation,
concurrent sends in one chat, imported histories, or duplicated/forked chats in
OW1. They can append duplicate turns or diverge from canonical history. Enforced
operation/history detection requires a later design; this implementation does not
claim it.

## Deployment preparation (not executed)

`compose.ow1.yml` is an inert review artifact; it is separate from the existing
Corvus Compose files. Do not pull/start it until deployment is separately approved.
Its Linux host network makes the validated loopback endpoint reachable; normal
Docker bridge loopback would refer to the container instead. The proposed Open
WebUI bind is `127.0.0.1:3001`, with a separate named volume and no auto-restart.
Check that port's availability during deployment. It mounts no Corvus data or
llama.cpp endpoints. Host networking grants access to host loopback services;
only trusted admins should manage Functions, which execute Python code.

For a later deployment review:

1. Keep authentication enabled, bootstrap the administrator locally using
   v0.6.5's first-user flow, and keep public signup disabled. Plan any ingress
   separately; OW1 adds no public bind, proxy route, or TLS configuration.
2. Verify persisted Open WebUI settings: v0.6.5 PersistentConfig can retain values
   that override environment defaults after the first run. Keep OpenAI, Ollama,
   arena models, title, tags, and autocomplete disabled. Configure no external
   model, task model, tool server, filter, action, knowledge collection, or file
   retrieval pipeline.
3. Import `corvus_pipe.py` as a **Function**, enable it, and configure its admin
   valves. For acceptance, set `CORVUS_CHAT_URL` to
   `http://127.0.0.1:18096/api/chat` **before sending any chat** and use a distinct
   acceptance `INSTANCE_ID`. The default port 8096 is production and is never an
   acceptance target. Select only the Corvus Pipe as the chat model. Disable the
   model's vision, file upload, web search, image generation, code interpreter,
   and tool capabilities and permissions; leave Open WebUI memory injection disabled.
4. Keep feature/operation controls disabled or unused. Middleware can perform
   retrieval/tool/media work before invoking a Pipe, so Pipe rejection alone
   does not prevent that earlier Open WebUI work. Do not attach transforming
   filters or system/user prompt presets to the Corvus model.
5. In an approved isolated acceptance environment, verify saved-chat text turns,
   reconnect/resume, all unsupported-input rejections, task suppression, sanitized
   failures, and timeout behavior against canonical Corvus messages. Verify the
   original Corvus UI still operates unchanged. No live Open WebUI acceptance
   has been performed by the offline tests.

## OW2a isolated Corvus instance and OW2b filesystem hardening

Changing the port alone does not isolate memory. A **fresh process**, with its
environment set before Python imports Corvus, must use a separate data directory.
`memory/config.py` derives SQLite, LanceDB, and attachments from that directory;
startup schema preparation and dense recovery then operate only on acceptance
data. No production memory should be copied, seeded, mounted, queried, or used
as a fallback. In particular, do not copy the repository's old `data/` either.

The isolated instance uses the following settings. Open WebUI remains unstarted:

| Setting | Acceptance value |
| --- | --- |
| Separate service | `corvus-ow2a-acceptance.service` (manually started; not enabled) |
| API bind | `127.0.0.1:18096`, one worker |
| `CORVUS_DATA_DIR` | `/home/ethan/srv/data/corvus/ow2a-acceptance` |
| SQLite | `/home/ethan/srv/data/corvus/ow2a-acceptance/corvus.db` |
| Dense index | `/home/ethan/srv/data/corvus/ow2a-acceptance/corvus-retrieval.lancedb` |
| Attachments | `/home/ethan/srv/data/corvus/ow2a-acceptance/attachments` |
| Pipe `CORVUS_CHAT_URL` | `http://127.0.0.1:18096/api/chat` |
| Pipe `INSTANCE_ID` | `corvus-open-webui-ow2a-acceptance` (never the production ID) |
| Initial Pipe `WEB_MODE` | `off`; web-mode cases only after isolation is verified |

The authoritative acceptance-only unit is
[`deploy/systemd/corvus-ow2a-acceptance.service`](../systemd/corvus-ow2a-acceptance.service).
It matches the installed, verified OW2b unit byte for byte, including its literal
host paths and user. Prepare the isolated directory and complete offline cache
before installing it. It is not a production-unit override.

Check the repository artifact against the installed unit without changing either:

```bash
cmp deploy/systemd/corvus-ow2a-acceptance.service /etc/systemd/system/corvus-ow2a-acceptance.service
systemd-analyze verify deploy/systemd/corvus-ow2a-acceptance.service
```

Filesystem restrictions provide a second boundary: production/private memory,
demo memory, and repository-local legacy memory are inaccessible inside this
service's filesystem namespace. `ProtectSystem=strict` alone leaves `/home`
writable; `ProtectHome=read-only` closes that exemption. The source repository,
its virtualenv, and both isolated cache directories are explicitly read-only.
Only the acceptance data root outside those cache directories is writable in the
persistent filesystem; systemd's private temporary directory remains available.
There is no autostart/install section or automatic
restart. No Nginx/public route, UI change, container, or database migration is
needed. `compose.ow1.yml` remains an unstarted Open WebUI manifest; the Pipe
endpoint is configured as an admin valve, not a Compose environment variable.

Prepare the complete offline cache, including the pinned model's generated
Transformers modules, before making it read-only. `PYTHONDONTWRITEBYTECODE=1`
prevents runtime bytecode writes. Prove that the prepared cache loads and encodes
a synthetic string while read-only inside the actual service mount namespace;
do not grant cache write access merely to hide missing assets. Cache changes
require separate preparation while acceptance is stopped. The live filesystem
check must also demonstrate failed source/virtualenv/cache writes, successful
temporary create/write/remove under the acceptance data root, and denial of all
three canonical memory roots. Restart only the acceptance unit after changes.

After separate deployment approval, the planned sequence is:

1. Verify that port 18096 is unused and inspect the effective production
   `corvus-api.service` configuration without opening production databases.
   Confirm its resolved canonical data root is
   `/home/ethan/srv/data/corvus/private`; if it differs, include the actual root in
   the acceptance unit's deny list before proceeding. Verify all denied paths
   exist and the acceptance root has no symlinks, hardlinked files, bind mounts,
   or overlap with production, demo, or repository memory roots.
2. Create a **new, empty**, mode-0700 acceptance directory owned by `ethan`.
   Prepare its own embedding cache with only the pinned model assets required by
   `memory/dense_index.py` (`Alibaba-NLP/gte-multilingual-base`, revision
   `ca1791e0bcc104f6db161f27de1340241b13c5a4`), without copying canonical memory or
   a dense index. Confirm the cache works offline before live turns. No packages
   or model assets have been installed/copied in OW2a.
3. Review/install only the separate acceptance unit, then start only that unit.
   Validate the actual process environment and all four resolved memory paths,
   the loopback listener, empty acceptance sessions, and lack of readable/writable
   production paths inside the service namespace. Refuse live acceptance if any
   isolation check fails. Production `corvus-api.service` stays running unchanged.
4. Configure the acceptance Pipe endpoint and instance ID before any Open WebUI
   chat. Installing/starting Open WebUI requires its own approval. Run synthetic
   acceptance turns, inspect only acceptance canonical messages, and verify
   persistence, resume, task suppression, rejection, and timeout behavior there.
5. Stop only the acceptance unit when finished; retain its synthetic data for
   review. Do not stop, restart, reset, or migrate production services or memory.

The acceptance Corvus API can reuse the running model server on 8095 through the
normal `process_turn()` path. Open WebUI still never connects directly to it.
Sharing model inference does not share the SQLite/LanceDB memory root, but CPU,
RAM, and model queue contention can affect production latency; schedule live
acceptance accordingly. Model cache preparation and filesystem-namespace checks
are deployment prerequisites, not claims of completed live validation. The
production endpoint remains the default for compatibility, so explicit valve
verification is mandatory before acceptance traffic. OW1's regenerate/branch and
uncertain-timeout limitations remain unchanged.

## Offline verification

From the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -p test_open_webui_pipe.py -v
git diff --check
```

The suite loads the deployable Function file, runs HTTPX mock transport contracts
for default and acceptance destinations plus rejected endpoint forms,
and exercises the real `/api/chat` ASGI route with `process_turn()` stubbed. It
does not contact production, run a model, write production memory, or install
Open WebUI. Existing tests are mostly executable contract scripts; run them in
separate processes with a temporary `CORVUS_DATA_DIR` to avoid test module state
and runtime-data interference. The OW2a path test starts only a short-lived Python
subprocess, selects a temporary data root before imports, checks the store/dense/
attachment paths, and writes a synthetic row there. It starts no service, loads no
embedding model, and reads no production memory. OW2b endpoint health and empty
acceptance storage were checked on 18096; no live Open WebUI chat has run.

Contract checked against the pinned upstream sources:
[Pipe injection](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/open_webui/functions.py),
[request metadata](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/open_webui/main.py),
[middleware](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/open_webui/utils/middleware.py),
[tasks](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/open_webui/routers/tasks.py),
[chat payloads](https://github.com/open-webui/open-webui/blob/v0.6.5/src/lib/components/chat/Chat.svelte),
[settings](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/open_webui/config.py),
and [container entrypoint](https://github.com/open-webui/open-webui/blob/v0.6.5/backend/start.sh).
