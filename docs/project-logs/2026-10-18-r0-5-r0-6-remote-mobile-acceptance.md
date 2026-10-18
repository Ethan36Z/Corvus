# R0.5 / R0.6 — Remote HTTPS and initial iPhone PWA acceptance

Checkpoint date: 2026-10-18. Branch: `lab/ow2e-console`.
Documentation baseline: `c43412ce8a3101178d44464164d7aac1670e5e83`.
Milestone: **REMOTE_PERSISTENCE_ACCEPTED**, scoped to one authorized synthetic
remote exchange and initial operator-confirmed iPhone PWA installation/session
behavior. This is not acceptance of all mobile or remote reliability scenarios.

## Delivery sequence and committed references

| Stage | Delivered boundary | Reference |
| --- | --- | --- |
| R0.1 | Infrastructure audit established the existing Tunnel/FoxGate and isolated Lab routing approach | Preparation baseline `7f389f183d01b6c1ad5e542b53a0132ee3cf1a0e`; no standalone R0.1 checkpoint log was found in this checkout. The committed R0.2 architecture record preserves the resulting design, not a separate R0.1 runtime acceptance claim. |
| R0.2 | Dedicated Lab FoxGate preparation | [Preparation log](2026-10-16-r0-2-lab-foxgate-preparation.md), commit `562433898f7f13a448c2b624bac24de305b38308` |
| R0.3 | HTTPS/PWA preparation | [Preparation log](2026-10-16-r0-3-https-pwa-preparation.md), commit `0f9094cde3cedd7731c06e8c23354195338cf82b` |
| R0.4 | Dedicated local FoxGate deployment and bounded authentication acceptance | [Deployment log](2026-10-17-r0-4-local-foxgate-deployment.md), commit `279688ed393a2376f079c03abec0ce39f91b5ff8` |
| R0.5 | Local HTTPS derivative activation, followed by operator-published routing and remote browser acceptance | [Local activation log](2026-10-17-r0-5b-https-local-activation.md), commit `c43412ce8a3101178d44464164d7aac1670e5e83`; public/browser evidence below supersedes that log's then-current remote-not-configured status |
| R0.6 | Initial iPhone PWA installation, standalone launch and retained login | Operator observations recorded below; mobile chat remains deferred |

## Remote route and evidence attribution

The operator manually added the published route using the existing Cloudflare
Tunnel. Public hostname: `lab-corvus.foxluma.com`; intended origin:
`http://127.0.0.1:8100`, the dedicated Lab FoxGate. Tunnel reuse/publication is
operator-provided context, not an independently audited Cloudflare Dashboard
change. No Tunnel, DNS or Cloudflare change was made by this checkpoint task.

The operator confirmed public HTTPS access, successful Lab FoxGate login,
loading of existing Open WebUI / Memory Arena UI-2, and an authenticated browser
Socket.IO connection returning HTTP 101. FoxGate and Open WebUI retain separate
authentication layers. The operator submitted one authorized synthetic test
requesting only the synthetic marker reply, and observed `Corvus remote OK`
automatically appear with a completed reply event (`done=true`). No duplicate
submission was observed. These are human browser observations, not automated
end-to-end browser tests.

The earlier automated precheck validated TLS hostname/certificate trust using
TLS 1.3, but public HTTP requests returned Cloudflare 403 Access denied,
including the login page. That client-specific automated-probe restriction
coexists with successful operator browser access. It does not establish public
FoxGate redirects or authenticated asset delivery from the automated client.
Local checks verified relative login redirects without loopback URLs,
unauthenticated denial, internal-verify protection and unknown-host rejection.

Earlier gateway logs contained eight Socket.IO 502s with upstream connection
refusals at 06:36:50–06:37:28 UTC near container startup, followed by a 101 at
06:41:08 UTC. Subsequent operator-observed authenticated 101 and reply delivery
establish the scoped successful exchange, not uninterrupted socket reliability.

## Independent persistence layers and synthetic reconciliation

The preceding read-only audit used SQLite URI `mode=ro` and `query_only=ON`.
Queries selected the exact authorized synthetic message and its linked records;
no private chats, complete rows, credentials or recalled memories were printed.

- **Open WebUI history — CONFIRMED:** one matching saved chat, one exact user
  node, one linked assistant node containing the expected synthetic reply, and
  assistant `done=true`. History lives in persistent WebUI `webui.db` chat JSON.
- **Lab API processing and canonical evidence — CONFIRMED:** Lab SQLite
  `/home/ethan/srv/data/corvus/lab/corvus.db` contains user evidence ID **49**
  at **2026-10-18 07:15:02 UTC** and matching assistant evidence ID **50** at
  **07:15:03 UTC**. The Pipe-derived WebUI session identity matches this pair.
- **Canonical contract — CONFIRMED:** the runtime commits user evidence first
  and commits assistant text separately after generation. The Pipe validates a
  successful model response and `persistence=NORMAL` before returning the reply.
  UI history and canonical evidence are independently stored; a UI message does
  not imply exactly one assertion, index entry or Hindsight memory.
- **Duplicate evidence — scoped absence observed:** one exact user match and
  one exact assistant match in canonical storage, one linked WebUI pair and one
  retain intent. No duplicate canonical pair was observed. Exactly-once
  processing/delivery is **NOT_CONFIRMED**; there is no Pipe request idempotency
  key, and a successful response alone cannot prove that guarantee.

The derived shadow audit path is
`/home/ethan/srv/data/corvus/lab/h1-shadow-recall.jsonl`. Runtime async retain is
enabled. Linked evidence records shadow recall **OK**, without error, at
**07:15:04.709821 UTC**, durable retain intent at **07:15:04.713345**, submission
acceptance at **07:15:04.769106**, and retain outcome **ACCEPTED** without error
at **07:15:04.781649**. One linked operation ID was observed. Passive Hindsight
logs contain linked completion evidence at **07:15:37.910514 UTC**, after the
main canonical reply, consistent with the background lifecycle.

Retain attempt/acceptance and passive completion evidence are **CONFIRMED**.
Independently queried durable Hindsight terminal status is **NOT_CONFIRMED**.
A newly extracted Hindsight memory is **NOT_APPLICABLE** as a requirement for
this test: derived extraction need not produce a new personal fact. No recall,
retain, replay, reconciliation or operation-status API was invoked by the audit;
the status endpoint may update parent bookkeeping and was deliberately avoided.

## Initial iPhone PWA acceptance

The operator confirmed iPhone Safari public access, installation to the home
screen, standalone app launch, and retention of the login session. These are
operator observations; no automated iPhone test was executed.

| Capability | Status |
| --- | --- |
| REMOTE_BROWSER_CHAT_DELIVERY | PASS — operator-observed delivery, supported by read-only persistence reconciliation |
| IPHONE_PWA_INSTALL | OPERATOR_CONFIRMED |
| IPHONE_STANDALONE | OPERATOR_CONFIRMED |
| IPHONE_SESSION_PERSISTENCE | OPERATOR_CONFIRMED |
| iPhone actual chat delivery | NOT_YET_ACCEPTED |
| Independent logout and session expiry | NOT_YET_ACCEPTED |
| Missed-result recovery after disconnect | NOT_YET_ACCEPTED |
| Requests exceeding Cloudflare timeout | NOT_YET_ACCEPTED |
| Long-duration reliability | NOT_YET_ACCEPTED |

## Isolation, operations and recovery

Lab has dedicated FoxGate credentials/signing material and separate Lab data,
WebUI volume and API. R0.4 verified Lab-session rejection by Demo/Private;
reverse-direction Demo/Private-session rejection by Lab remains unverified.
This checkpoint does not upgrade that incomplete realm-isolation matrix.

Prior and reconciliation listener inventories match: Lab gateway 8100, Auth
8101, WebUI 3003, API 18096, Qwen 8095 and Hindsight 8888/9999 remain bound to
loopback. No direct public backend listener was observed. Current relevant
container identities/start times match the earlier audit, with no restart by
this task. Production/Demo health remained unchanged. Lab/Private/Demo canonical
database fingerprints matched across the final read-only audit window; this is
bounded evidence, not an exhaustive historical data-change audit. The synthetic
pair and linked shadow writes were previously authorized test activity.

Recovery references are retained in the R0.5b activation log:

- Protected WebUI backup:
  `/home/ethan/srv/backups/corvus-lab/r0-5b-20261017T075739Z/lab-webui-data.tar`.
- Persistent volume: `corvus-lab-open-webui-data`; protected environment file:
  `/home/ethan/.config/corvus-lab/webui.env` (contents excluded).
- Lab gateway runtime configuration:
  `/home/ethan/srv/infrastructure/lab-access`.
- WebUI configuration rollback uses the original cached UI-2.1 image and
  webui + boot + arena-ui2 Compose files, omitting the HTTPS override, while
  preserving the existing volume and signing configuration. See the activation
  log for exact commands and backup validation/recovery boundaries. No rollback
  or restore was performed here.

The local FoxGate login page still contains Demo wording, confirmed by a
read-only page check during finalization. This is a non-blocking branding issue;
no FoxGate template or credential change is included.

## Reliability constraints and final validation

The Pipe's 300-second HTTPX I/O timeout is not a whole-turn deadline. WebUI
background task state is in-process, not durable recovery state. Nginx's
600-second timeout does not remove the documented Cloudflare default
125-second origin-read constraint; the current account-specific setting was not
independently inspected. Reconnect does not guarantee missed-final recovery;
disconnect, cancellation or timeout does not prove canonical writing stopped.
Never automatically retry an uncertain turn.

Finalization verified the expected clean baseline and healthy running Lab
containers. Read-only HTTP checks returned 200 for Lab WebUI/API, Lab Auth,
Hindsight, Qwen, and Production/Demo APIs. Existing offline FoxGate deployment
and HTTPS/PWA contract suites each passed all **7 tests** (**14 total**), using
the existing local pinned upstream archive without downloads. The expected
negative-path persistence diagnostic in the HTTPS suite did not indicate a test
failure. Git whitespace, secret-safety and staged-scope reviews precede the
single-file documentation commit.

No additional chat, database/memory write, service restart, deployment,
Cloudflare/DNS change, credential change, commit to runtime configuration or Git
push is part of this finalization. Only this new checkpoint is staged/committed.
