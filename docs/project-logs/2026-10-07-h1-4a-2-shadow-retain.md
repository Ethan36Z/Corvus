# H1.4a-2 — Shadow retain implementation (offline validation)

Hindsight remains derived memory. Corvus SQLite message IDs and history stay
canonical. The live API contract was established in H1.4a-1 against local API
0.10.1 and installed container source; this step uses no live writes.

## Data and execution

The existing post-response background task runs recall, appends and fsyncs the
comparison JSONL record (including its directory), then performs one retain.
Terminal recall OK/TIMEOUT/ERROR permits retain after the durable append.
An append/fsync failure skips retain and logs COMPARISON_APPEND_FAILED through
application logging. Recall and retain are not independently scheduled.
Failed partial appends are rolled back under the file lock. An existing
incomplete JSONL tail blocks further appends/retains until operator repair;
this flow does not silently repair crash-truncated evidence.

The retain reads the two canonical rows through a read-only SQLite connection,
checks IDs/session/roles/nonempty text/timestamps, and sends exactly one item:

```text
User:
<canonical user text>

Assistant:
<canonical assistant text>
```

POST /v1/default/banks/corvus-hindsight-lab-v1/memories uses `async:false`,
`document_id:corvus-lab:turn:<user_id>:<assistant_id>`, the assistant's canonical
UTC timestamp, and string-valued metadata: source, session_id, user_message_id,
assistant_message_id. It sends no native role field and exposes no Hindsight ID
as a Corvus ID. Invalid or unavailable canonical data skips HTTP entirely.

## Deadline and failure isolation

Recall retains its 10-second deadline. Retain uses a **provisional 390-second**
HTTP deadline: two configured 180-second local model calls for modest chunking,
plus 30 seconds for embedding/database overhead. The local configuration has
LLM concurrency 1 and a 4096-token retain completion cap. A historical bulk
benchmark took 2027 seconds for 18 operations; that does not establish a
single-turn bound. Long inputs, contention, or server-side processing retries
may exceed this provisional allowance. No latency measurement is claimed.

There is one client POST, zero transport/application retries, and no polling.
Timeout is TIMEOUT/DEADLINE_EXCEEDED_WRITE_COMPLETION_UNKNOWN. Cancelling the
client wait does not prove the server stopped writing. Malformed responses and
HTTP/transport errors remain derived ERROR outcomes. No second retain is issued
for a failure in this flow. This is not a durable exactly-once system across
external rescheduling or process restarts.

Retain performs model extraction and embeddings. This bank's automatic
observation consolidation is enabled, so subsequent server-side synthesis can
continue even after synchronous retain succeeds. No reflect request is made.
These calls can contend with the shared local model even though the current
visible reply has already been sent.

## Append-only derived observation format

Existing schema-version-1 comparison fields remain intact. A comparison adds
`retain:{status:SKIPPED,elapsed_ms:0,document_id:...,error:RETAIN_NOT_STARTED}`.
That is the pre-retain snapshot, not its final outcome.

A second compact JSONL entry in the same file has `record_type:retain_outcome`,
schema_version, recorded_at, session_id, canonical user/assistant IDs, and the
final retain section (status, elapsed_ms, document_id, error). It repeats no
query, recalled text, or assistant text. Readers distinguish outcome events by
record_type and join on canonical IDs; old comparison records remain readable.

If comparison durability fails, no Hindsight mutation is attempted. Application
logging is the remaining channel for the skipped reason; JSONL itself may be
unwritable. If retain finishes but outcome append fails, application logging
reports its status and canonical linkage. The comparison then still says
RETAIN_NOT_STARTED, so absence of a completion event is **not evidence that no
write occurred**. A crash between HTTP and outcome append has the same ambiguity.
Neither case changes canonical history, the reply, working context, retrieval,
or model status. This background flow is best effort and can be interrupted by
process termination.

## Acceptance boundary

Validation is offline with isolated temporary databases/logs and mocked retain
HTTP. No service restart, live Hindsight retain, deployment/configuration
change, reboot/shutdown, commit, or push is part of this coding step. Running
service acceptance remains a separately authorized future step.

Offline checks: 25 shadow/retain unittest cases, five historical-memory cases,
and import-time assertions across the selected conversation/API/working-context
regression modules. The shadow suite runs outside the execution sandbox because
a minimal Starlette threadpool call stalls inside that sandbox; HTTP remains
mocked in both environments. `git diff --check` is clean.
