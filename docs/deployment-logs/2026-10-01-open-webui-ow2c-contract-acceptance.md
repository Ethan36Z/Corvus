# Open WebUI OW2c contract acceptance

**Result: OW2c contract acceptance passed** on 2026-10-01. Open WebUI v0.6.5
used the `corvus_pipe` Function Pipe and its configured endpoint
`http://127.0.0.1:18096/api/chat`. Port 18096 served the isolated Corvus
acceptance data root. Production Corvus at `127.0.0.1:8096` remained healthy
and untouched.

| Acceptance case | Result | Evidence |
|---|---|---|
| Saved-chat reload and session stability | PASS | Reading the saved chat preserved its user/chat identity and deterministic `ow1:` session mapping; no extra turn was needed. |
| Different-chat identity | PASS | Saved chats A and B map to distinct Corvus sessions; each contains one user and one assistant message. |
| Recent-context isolation | PASS | Chat B had no earlier messages in its session. Read-only reconstruction returned `recent_message_ids=[]`. |
| Attachment rejection | PASS | A file descriptor without uploaded bytes was rejected at the Pipe boundary. Corvus counts stayed at 2 for B and 4 total. |
| Acceptance backend unavailable / no fallback | PASS | A request while only the 3001 container's route to 18096 was temporarily rejected returned the sanitized failure, no assistant reply, and no persisted turn. The rule was removed and 18096 health restored. |

Chat identities and canonical Corvus counts:

| Open WebUI chat ID | Corvus `ow1:` session ID | Messages |
|---|---|---:|
| `b629e2b5-3f99-4199-8cac-bcec7bf93694` | `ow1:40bdeaecd0ad5ed250d49dae0285de07a2c0aec6c958bc54b857ab88276f44e0` | 2 |
| `5595233d-9e3a-44ea-97e1-818e133eb746` | `ow1:4d7632bbbbc697ae68d0e0fe4be1b3ac9410118b8bd116fd4a51e09a2d486e23` | 2 |

Recent conversation context is session-scoped. Historical evidence retrieval is
intentionally cross-session and is supplied only through Corvus's explicit
historical-evidence path; it is not ordinary recent chat context. **Successful
live historical recall was not verified:** the isolated acceptance dense index
did not contain `evidence_dense_v1`, and read-only reconstruction reported
retrieval `DEGRADED` with no historical message IDs. Retrieval degradation is
permitted by the OW1 contract. This result does not demonstrate historical
recall success, and no session filter was added.

OW2c was a private, single-user acceptance. Multi-user memory isolation is not
implemented or claimed; it requires a separate user/tenant namespace design.
Hindsight was not involved in the Pipe or these acceptance requests. No
regenerate, edit, branch, or idempotency behavior was exercised; those remain
outside OW2c.

At final verification, both Corvus endpoints were healthy, production's PID and
start time were unchanged, and metadata for all 445 production memory files
matched the pre-verification snapshot. Both saved Open WebUI chats and all four
isolated canonical messages were unchanged after the rejection tests. The
OpenAI, Ollama, and direct-connection backends were disabled; `corvus_pipe` was
the only enabled model/function and retained the 18096 endpoint.
