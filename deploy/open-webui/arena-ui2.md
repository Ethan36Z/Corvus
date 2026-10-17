# Memory Arena UI-2 — prepared Lab vote overlay

UI-2 adds two preference buttons to the existing Memory A/B panel. It is a
separate patch after the accepted UI-1 overlay. The UI-1 patch, Production
image, active compose files, Corvus chat path, H1, and retain behavior are
unchanged. This change is prepared for diff review; it is not deployed.

The buttons appear only after the authenticated Open WebUI chat response
confirms that a completed, votable Arena message is saved in an editable
chat. Eligibility uses a detached set of trial IDs rebuilt from saved server
responses after load or successful history persistence. Local Arena events
cannot add IDs, including when local and loaded history share an object.
Failed saves leave new trials ineligible. They call `POST /api/chat/actions/corvus_arena_vote` using Open WebUI's
existing authenticated API path. That dedicated Action route reads the saved
chat by authenticated user ID and checks its assistant message, Pipe model,
completion, and matching votable trial ID. It forwards only `trial_id` and
`choice` to the fixed Lab Corvus `/api/arena/vote` URL. It does not proxy an
arbitrary destination, invoke chat generation, or write canonical messages.
The browser does not address Corvus directly.

A failed vote leaves the panel and chat untouched. After Corvus confirms a
vote, the Action patches only `corvus_arena.vote` in the original saved chat
message with one conditional SQLite JSON update. The update rechecks owner,
message, and votable trial identity at write time. Navigation cannot retarget
it, and it cannot replace a newer chat snapshot. The existing per-message
route accepts only `content` and changes `history.currentId`, so it is not
suitable for this marker. A full-chat read/write would risk replacing newer
content. The Action returns `marker_persisted` separately from the durable
Corvus vote. A failed marker update is reported without retry or a misleading
chat-list error. Refresh restores a confirmed marker; no vote remains absent.

Corvus already supports append-only re-voting. The latest valid event per trial
is effective. UI-2 exposes only `rag` and `hindsight`; legacy `tie` and
`neither` values remain accepted by the existing backend for compatibility.
`GET /api/arena/preferences/daily?date=YYYY-MM-DD&time_zone=Area/City` is a
read-only Lab contract. The browser can provide its local calendar date and
`Intl.DateTimeFormat().resolvedOptions().timeZone`; Python `zoneinfo` applies
the corresponding day boundary. The output is exactly `date`, `rag`,
`hindsight`, and `total_votes`. It counts each trial's latest effective actual
preference vote only when that event falls on the requested local day. Trials
without votes and effective tie/neither values contribute zero. The UI does
not request or display aggregate scores.

`branding/arena-ui2.lock.json` pins the UI-1 base, UI-2 patch, and before/after
source hashes. `verify_branding.py --arena-ui2` checks and prepares both layers.
`Dockerfile.arena-ui2` and `deploy/lab/compose.arena-ui2.yml` are prepared
Lab-only build inputs and do not alter the running installation.

Known trust limit: Open WebUI's stored chat history is writable by its owning
user. The Action's ownership check proves that a matching Arena message is
available to that authenticated account, but it cannot independently attest
that the saved trial association originated from the Arena emitter. Corvus
still requires the trial to exist and be votable.
