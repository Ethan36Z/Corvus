# OW2e-A Minimum Durable Lab — Linux acceptance

Result: **OW2e-A FINAL PRODUCT ACCEPTANCE PASSED**, 2026-10-03 PDT.
Stopped for final seal review; no staging, commit or push.

The OS-level destination guard is deferred by the operator's explicit instruction.
No guard installer was executed. No dedicated slice/cgroup or guard unit/config
was installed, and no nftables/iptables/firewall mutation command was issued.
The prepared guard files remain inactive drafts in /tmp. The Compose configuration
has no custom cgroup parent. Docker uses its normal container cgroups.

## Running deployment

| Item | Accepted value |
|---|---|
| Console | http://127.0.0.1:3003, loopback IPv4 only |
| Container | corvus-lab-open-webui; running and healthy |
| Image | corvus-open-webui:0.6.5-ow2d.1 |
| Verified image ID | `sha256:52c80cb880eb4482f12e6df2b0dec55326a57fdf94fabb3184b76b7afb918b1b` |
| New external volume | corvus-lab-open-webui-data |
| Compose | deploy/lab/compose.webui.yml |
| Admin login | admin@corvus-lab.invalid |
| Private credentials | /home/ethan/.config/corvus-lab/admin-bootstrap.json, mode 0600 |
| Stable authentication secret | /home/ethan/.config/corvus-lab/webui.env, mode 0600 |
| New stable INSTANCE_ID | `corvus-lab-console:eaa8d741-998d-41f6-ae5b-9019748c0a26` |
| Only active Function/model | corvus_pipe / Corvus |
| Pipe checksum | 37d1f6ea3adab2f16f02ccb4e7e1abef9949544d871a581c791263bc8698b781 |
| Pipe destination | http://127.0.0.1:18096/api/chat |
| Other valves | WEB_MODE=off; TIMEOUT_SECONDS=300 |
| Lifecycle | Lab API enabled; Docker restart=unless-stopped; controlled reboot product acceptance passed; firewall semantic persistence deferred |

The new admin and checksum-identical Pipe were initialized offline in the fresh
volume before WebUI first started. Signup stayed disabled throughout deployment.
Authentication, endpoint validation and fixed configured Lab valves are active.
OpenAI, Ollama, direct connections, arena models and alternate providers are
disabled; corvus_pipe is the sole available model. No tools, filters, actions,
knowledge configuration or Hindsight integration was added. Model upload/media/
search/code capabilities are false, automatic generation tasks are disabled and
the admin's WebUI memory preference is false. Environment configuration is
authoritative on startup (ENABLE_PERSISTENT_CONFIG=false).

## Acceptance evidence

| Case | Result | Evidence |
|---|---|---|
| Branding/login | PASS | Installed headless Chrome displayed Corvus title/artwork/sign-in; new admin authenticated. HTML/PWA name also Corvus. |
| Signup disabled | PASS | UI has no signup link; unauthenticated signup HTTP 403. |
| Only Corvus Pipe | PASS | Rendered selector contains one model; authenticated model/Function lists contain only corvus_pipe. |
| Endpoint validation | PASS | localhost-form valve update HTTP 400; all valves remained unchanged. |
| First chat persistence | PASS | Browser sent one ordinary turn; WebUI stored user/reply; Lab stored exactly 2 canonical messages. |
| Reload | PASS | Real browser reload restored the same identity and reply with no added canonical message. |
| Resume | PASS | Same browser chat recalled amber-cove-472; same Corvus session then held 4 messages. |
| Distinct chat | PASS | Second browser chat mapped to a distinct ow1 session and stored 2 messages. |
| Recent-context isolation | PASS | Read-only reconstruction using sealed recent-context selector/SQL loader: first B turn recent IDs=[]; resumed A turn recent IDs=[1,2]. |
| Attachment rejection | PASS | Non-uploaded file descriptor rejected at Pipe boundary; all 6 canonical messages unchanged. |
| Alternate-model rejection | PASS | Unknown model HTTP 400; no canonical message or fallback. |
| Backend unavailable | PASS | Temporary WebUI-only connect failure to 18096 rendered fixed sanitized error, no assistant reply, no canonical write. |
| Restart persistence | PASS | Normal container recreated on same external volume; both successful chats and all 6 canonical messages unchanged; real browser restored both A replies and remained authenticated. |
| Production process/data | PASS | PID 5711, start ticks 2640; all 445 file SHA256/size/mtime values matched baseline before, during and after acceptance. |
| Original 3001/3002 | PASS | Both stopped, restart=no, original IDs/mounts retained; immutable read-only SQLite quick_check and DB SHA256 match recovery copies. |

Chat A: `7f09c43e-aff3-49f6-8768-a4ac688bff86` -> `ow1:2e6bb7f642b8768c59a5f6280b2d13c41005e8b02ee725b6a8bd109a43968b3d` (4 messages).

Chat B: `efe5559e-adb7-4dff-9d7b-851751e9234c` -> `ow1:b1763979353747a58ef2223988e979a0dbe35cdb1784c275fe86c100e33f31a6` (2 messages).

Failed-backend UI chat: `c5d12246-9dc8-49d8-8333-c4d0f2aa7b3c`. It retains the
synthetic failed display turn/error, with no canonical Corvus session messages.
Successful synthetic acceptance history is intentionally retained for review.

The backend-unavailable test temporarily recreated only the new Lab WebUI with
a small LD_PRELOAD fixture that returned ECONNREFUSED only for that process's
IPv4 connect calls to 127.0.0.1:18096. The API stayed active at PID 1706007 with
start ticks 8265215 and answered host health checks. The sealed Pipe and its
endpoint/timeout/instance valves were unchanged. No firewall or cgroup changes
were used. Normal Compose was restored in finally; the final container has no
LD_PRELOAD setting, test mount or test library, and mounts only the new volume.

Recent-context reconstruction used an immutable read-only Lab SQLite connection
and the exact sealed selection functions, with a word-count estimate for the
small test context's generous budget. It establishes session-scoped recent
context, not tenant isolation or absence of cross-session historical retrieval.
Live historical recall and unsupported regenerate/edit/branch controls were
not accepted; those remain outside this contract.

## Review artifacts

Screenshots and structured evidence are in deploy/lab/acceptance:
01-lab-login.png; 04-lab-sole-model.png; 05-lab-first-chat.png;
07-lab-resume-confirmed.png; 08-lab-distinct-chat.png;
09-lab-unavailable-sanitized.png; 10-lab-restart-persistence.png;
acceptance-evidence.json; webui-final-inventory.json;
retained-webui-final-audit.json.

At the original deployment/Linux-acceptance checkpoint, no sudo, boot persistence,
commit, push, original-volume merge/reuse or Hindsight integration was performed.
The later approved boot promotion is recorded below. Production source/working tree remains clean at
f453ed161994c8131bf8d9ed7c43cc15914176cf.

## Historical pre-promotion deployment review — 2026-10-03

Current topology, effective provider/endpoint controls, retained containers and
production invariants were rechecked read-only. All remain as accepted above.
Proposed commit artifacts passed the credential review; private admin/signing
credentials, tokens/cookies, runtime databases and the production baseline are
outside the repository. Screenshots contain empty login fields and synthetic
test content only.

The operator previously confirmed the privileged Lab namespace acceptance:
Lab mount namespace with pinned FD; UID/GID 1000; cleared groups/capabilities;
no-new-privs; read-only code/cache; unnamed O_TMPFILE Lab-data write/seek/read/close
with no named fallback; production PID/data unchanged before and after.

The API's existing installed unit supports enablement but remains disabled;
Docker WebUI restart remains no. A validated boot-persistence proposal is in
boot-persistence-review.md, with an inactive compose.boot.yml override and a
byte-identical corvus-lab-api.service source snapshot. No sudo command, enablement,
restart or reboot was executed for this final review. Reboot startup is not yet
an acceptance result. No commit or push has been made.

## Approved boot-persistence promotion — 2026-10-03

The operator ran sudo systemctl enable corvus-lab-api.service after the automation
could not authenticate non-interactive sudo. Enablement and active state were
verified independently. docker update --restart unless-stopped was applied to
only corvus-lab-open-webui. API PID/start ticks (1706007/8265215) and the existing
healthy WebUI container/start time remained unchanged. Both Lab endpoints remained
loopback-only and healthy. Production PID/start ticks/time, all 445 baseline
SHA256/size/mtime values and retained stopped 3001/3002 restart=no were rechecked.

At this historical promotion checkpoint, the durable private reboot baseline
was outside the repo, mode 0600. The prepared checker passed --before-reboot.
Its --after-reboot mode had not yet run. No reboot,
production/model/Hindsight/firewall/cgroup changes, staging, commit or push occurred.
Current lifecycle is recorded in deployment.json and
acceptance/boot-promotion-verification.json; the exact manual reboot, post-reboot
checks and rollback commands are in reboot-acceptance-plan.md.


## Final controlled reboot product acceptance — 2026-10-03 PDT

**OW2e-A FINAL PRODUCT ACCEPTANCE PASSED.** The operator completed the
controlled reboot. This result accepts Minimum Durable Corvus Lab product and
runtime persistence under the operator-approved application-level boundary.
OS-level destination guard and firewall semantic persistence remain deferred
to the later hardening stage.

| Check | Final result |
|---|---|
| Boot identity | Changed from 6c9f90a3-4ce8-4515-9a72-d62eb2a700de to e8adb20c-f3df-41a5-976c-db8091ed9ccc |
| Lab API automatic return | Enabled/active, PID 5432, start 20:11:24 PDT; /api/health fully OK |
| Production automatic return | Enabled/active, PID 5373, start 20:11:23 PDT; /api/health fully OK |
| Lab WebUI automatic return | Same healthy container, verified branded image and persistent volume; restart=unless-stopped |
| Bindings | Exactly 127.0.0.1:8096, 127.0.0.1:18096 and 127.0.0.1:3003 |
The initial reboot exposed the dense bootstrap defect: incremental recovery
assumed evidence_dense_v1 already existed, so a missing table left the API
DEGRADED despite six canonical SQLite messages. The Lab fix adds an idempotent
create-if-absent helper using the pinned schema; it opens existing tables
unchanged, creates an empty table only when missing, and leaves progress tied
to successfully indexed canonical messages. Focused regressions and two Lab
API restarts verified bootstrap, resume and idempotency before this reboot.

| Dense persistence | Existing evidence_dense_v1 files retain pre-reboot SHA256/size/mtime; pinned schema and 768 dimensions |
| Dense readiness | Six unique rows cover exactly six canonical messages; progress=6; caught_up=true; no duplicates |
| Saved history | Both saved chat hashes and all six canonical messages match the original baseline |
| Real browser reload | Installed headless Chrome opened A, reloaded A and opened B; retained replies visible with Corvus branding; no new turn sent |
| Provider boundary | Sealed corvus_pipe unchanged and targets only Lab 18096; sole model; OpenAI/Ollama/direct/tool-server paths disabled |
| No fallback | Prior accepted backend-unavailable/unknown-model no-fallback evidence retained; sealed Pipe unchanged; no new outage test or chat turn |
| Lab namespace | Original unit hash unchanged; denies production checkout/private/demo/old acceptance data; ProtectSystem=strict and NoNewPrivileges=yes |
| Production data/source | All 445 durable SHA256/size/mtime values match; clean worktree at f453ed161994c8131bf8d9ed7c43cc15914176cf |
| Retained 3001/3002 | Original containers stopped, restart=no; no listeners |
| Model/Hindsight | Accepted container/configuration hashes unchanged; no Hindsight integration |
| HostConfig | PASS; only Dns, DnsOptions and DnsSearch null/[] equivalence; all substantive fields remain strict |
| Cgroups/guard | Accepted cgroup state matches; no custom OW2e cgroup/nftables destination guard installed |

### NON-BLOCKING / DEFERRED HARDENING

Runtime nftables/IPv4 iptables serialization/hash was not stable across reboot;
exact semantic equivalence was not established because the original evidence
stored hashes only. No actual exposure or policy defect was demonstrated.

The strict 180-second after-reboot checker stopped at
`Final reboot checkpoint mismatch: firewall_state`. Its result is retained as
a failure and is not relabeled as a full firewall/reboot-checker pass. Protected
firewall configuration files, firewall service state, IPv6 policy and the
141-rule count matched; nftables and IPv4 iptables runtime hashes differed.
Both original hashes and changed hashes are retained in the final evidence.

The operator explicitly classified this limitation as outside OW2e-A's Minimum
Durable Lab scope. No new semantic firewall framework, rule dump or additional
reboot was performed. Neither firewall state nor the checker or durable baselines
were rewritten to make a check pass.

### Final evidence and review

- `acceptance/post-reboot-browser-verification.json`: rendered Corvus browser
  text for both saved chats, successful A reload and equal before/after chat hashes.
  Screenshot capture stalled; this acceptance uses real rendered DOM evidence.
- `acceptance/final-product-verification.json`: independent re-run of the
  original invariants and non-firewall final checkpoint checks; boot/process
  identities, preserved dense state, production aggregate manifest hash, accepted
  namespace/provider state and unresolved firewall hashes.
- `acceptance/final-pre-reboot-verification.json` and
  `acceptance/final-reboot-checkpoint.json`: retained original final-reboot evidence.
- The private durable baseline retains SHA256
  `0013e30f9ae8a2340e2cb99905e2b8a4075fc6600096b084786a227b0f846307`.

Final credential scan and Git diff/whitespace review passed. Private admin/signing
credentials, auth tokens/cookies, runtime databases and browser profiles are
absent from proposed artifacts. Temporary headless browser profiles were removed
after use. Only synthetic saved chat text is retained in browser evidence.
Production data/configuration/services were not changed during this final review;
Lab API and production PID/start identities remained unchanged during validation.
No service restart, firewall/network/cgroup mutation, staging, commit or push
occurred. Stop for final seal review.
