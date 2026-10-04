# OW2e-A final controlled reboot acceptance

Final controlled reboot product acceptance passed on 2026-10-03 PDT.
The strict after-reboot checker retains its firewall_state mismatch. The operator
explicitly deferred firewall semantic persistence from Minimum Durable Lab scope.
See [ow2e-a-acceptance.md](ow2e-a-acceptance.md) and
acceptance/final-product-verification.json for the scoped final result.
No additional reboot, rule dump, checker change or baseline update is authorized.

## Historical final-reboot procedure (completed)

Final pre-reboot acceptance passed on 2026-10-03, before the controlled reboot.
The earlier controlled reboot exposed a missing dense-table bootstrap and an
overly strict DNS-list representation comparison. The accepted Lab corrections
passed isolated regressions and two Lab-only runtime restarts.

## Verified final pre-reboot state

- Current boot ID: 6c9f90a3-4ce8-4515-9a72-d62eb2a700de.
- Lab API enabled, active and fully healthy: PID 83912, start 19:48:50 PDT.
- Production enabled, active and healthy: PID 5078, start 18:52:22 PDT.
- Persistent evidence_dense_v1 uses the pinned 768-dimensional schema.
- Six unique dense rows cover all six unchanged canonical Lab messages;
  durable progress is 6. Dense files match the approved second runtime restart.
- Saved chat hashes match the original accepted history.
- Lab listeners are only 127.0.0.1:18096 and 127.0.0.1:3003; WebUI is healthy
  with its original container/image/volume and restart=unless-stopped.
- All 445 production hashes/sizes/mtimes match the original durable baseline;
  production source remains clean at f453ed161994c8131bf8d9ed7c43cc15914176cf.
- Original 3001/3002 containers remain stopped, restart=no, with original
  identities/mounts. Shared model/Hindsight configuration remains unchanged.
- Root read-only firewall evidence covers persistent UFW/nftables files,
  nft policy (141 rules), and IPv4/IPv6 iptables policy. Cgroup policy is captured.
- No additional restart, reboot, firewall/configuration mutation, commit or push
  occurred during final pre-reboot acceptance.

The original private baseline remains unchanged:
`/home/ethan/.config/corvus-lab/reboot-acceptance-baseline.json`.
The final checkpoint in `acceptance/final-reboot-checkpoint.json` anchors the
current boot/process identities, dense file hashes/sizes/mtimes, firewall and
cgroup state. It also seals the original baseline SHA256. It cannot rebase
production data or substantive configuration.

## Operator-controlled reboot

The corrected pre-reboot command passed:

```bash
python3 -B /home/ethan/srv/apps/corvus-lab/deploy/lab/check_reboot_acceptance.py --before-reboot --wait-seconds 180
```

Run manually in the Linux terminal:

```bash
sudo systemctl reboot
```

Do not stop WebUI beforehand and do not manually start or restart application
services after reconnecting. Automatic return must be observed.

## After reboot and reconnect

Once Docker is active, capture protected firewall evidence again. This helper
only reads rules/configuration and writes hashes to a new per-boot Lab evidence
file; it never changes firewall rules or services:

```bash
sudo python3 -B /home/ethan/srv/apps/corvus-lab/deploy/lab/capture_firewall_evidence.py
```

Then run the full checker as ethan:

```bash
python3 -B /home/ethan/srv/apps/corvus-lab/deploy/lab/check_reboot_acceptance.py --after-reboot --wait-seconds 180
```

The checker requires a different boot ID than the final checkpoint, enabled/
active services with new start times, healthy production and Lab endpoints,
exact loopback listeners, and the same WebUI container/image/volume/restart
policy. It independently checks persistent dense schema, canonical coverage,
metadata, six unique rows and caught-up progress=6. Dense files must retain their
pre-reboot hashes/sizes/mtimes, preventing a recreation/rebuild from masquerading
as preservation.

All original durable data/chat/unit/config checks remain strict. Only HostConfig
Dns, DnsOptions and DnsSearch allow null/[] equivalence. No substantive field is
ignored. Firewall comparison ignores ephemeral handles/counters and independent
declaration order, while preserving rule actions and order within chains.
Cgroup policy must match; the deferred guard must remain absent.

After automated PASS, open both saved Lab chats and reload chat A in the
installed headless browser. Confirm branding and retained replies without
sending, editing, regenerating or branching a turn. Chat A:
`7f09c43e-aff3-49f6-8768-a4ac688bff86`; chat B:
`efe5559e-adb7-4dff-9d7b-851751e9234c`.

Stop on any mismatch and capture evidence; do not repair or reset production,
change timeouts/baselines, rebuild dense state, recreate WebUI, or change model,
Hindsight, firewall or cgroups. No commit/push until final seal review.
