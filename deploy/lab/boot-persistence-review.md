# OW2e-A final deployment and boot-persistence review

Historical review prepared 2026-10-03; subsequently approved and promoted.
**Current state: Lab API enabled; Lab WebUI restart=unless-stopped; controlled
reboot product acceptance passed; firewall semantic persistence deferred.**
See [reboot-acceptance-plan.md](reboot-acceptance-plan.md) for the historical procedure and final acceptance limitation.

## Lifecycle at the pre-promotion review

- corvus-lab-api.service is active, PID 1706007/start ticks 8265215, but disabled
  at boot. Its installed unit already has WantedBy=multi-user.target.
- corvus-lab-open-webui is running and healthy with Docker restart=no.
- docker.service is already active and enabled at boot.
- The checked-in candidate corvus-lab-api.service is a byte-identical snapshot
  of the installed unit, SHA256
  0b5d187e3a9e2042a7faf8b9b5fbffe17532115febf31883acad0ae1ebd23c4c.
  No replacement unit, drop-in, new dependency or daemon reload is needed.

## Minimal proposed mechanism

Enable the existing Lab API unit. Let Docker manage only the Lab WebUI using
unless-stopped. compose.boot.yml is an explicit override containing only that
restart-policy change; the accepted compose.webui.yml stays unchanged.

This preserves the verified existing container/image, its fixed loopback bind,
the existing external volume, signing secret, admin, INSTANCE_ID and sealed
Pipe configuration. No volume creation, bootstrap, provider update or container
recreation is needed for promotion. Neither production nor the retained 3001/3002
containers is a command target.

Docker's existing boot enablement starts a running container with unless-stopped
after a daemon restart/reboot. An intentionally stopped Lab WebUI stays stopped
until explicitly started. API and WebUI startup are independent; Docker does not
order WebUI after API readiness. The accepted sanitized no-fallback behavior
covers early requests while the API is unavailable. There is no new WebUI
systemd unit and no competing container supervisor.

References: [Docker restart policy documentation](https://docs.docker.com/engine/containers/start-containers-automatically/)
and [Compose restart setting](https://docs.docker.com/reference/compose-file/services/#restart).

## Approved promotion commands (completed after review)

First validate the proposed Compose configuration (normal ethan account):

```bash
docker compose --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.webui.yml \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.boot.yml config --quiet
```

The only privileged command is:

```bash
sudo systemctl enable corvus-lab-api.service
```

This enables future startup without restarting the currently accepted API.
Then apply only the Lab container's restart policy, as ethan (already in docker):

```bash
docker update --restart unless-stopped corvus-lab-open-webui
```

Read-only verification:

```bash
systemctl is-enabled corvus-lab-api.service
systemctl show corvus-lab-api.service -p MainPID -p ExecMainStartTimestamp
docker inspect corvus-lab-open-webui --format '{{.Id}} {{.Image}} {{.State.Status}} {{.State.Health.Status}} {{.HostConfig.RestartPolicy.Name}}'
```

Recheck production PID/start ticks and its read-only data baseline, retained
3001/3002 state, and the three loopback listeners after promotion. Update the
deployment lifecycle record only after successful verification. A Linux reboot
has not been tested or authorized here; it would also restart production.

After promotion, always pass both Compose files for a start or recreation:

```bash
docker compose --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.webui.yml \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.boot.yml \
  up -d --no-build --pull never --wait --wait-timeout 180 open-webui
```

Using the base file alone for a recreation restores restart=no. A plain
docker compose restart does not change the existing restart policy.

## Final review findings

The acceptance report agrees with the final healthy branded image, external
volume, fixed 18096 Pipe valves, six canonical messages in two distinct sessions,
saved synthetic WebUI history and redacted runtime inventory. Its unavailable-
backend test fixture is absent from the final container. Historical-retrieval
and unsupported-control limitations remain explicitly documented.

The proposed files were checked against the actual private admin password,
stable signing secret and acceptance auth token; none occurred in their bytes.
Pattern and structured-JSON checks found no JWT, private key, bcrypt password
hash, bearer token, known API-key pattern or nonempty credential field. All seven
screenshots were visually reviewed: login fields are empty and chat content is
synthetic. UUIDs, INSTANCE_ID and SHA256 values are identifiers, not credentials.

admin-bootstrap.json and webui.env remain outside the worktree at
/home/ethan/.config/corvus-lab, owned by ethan, mode 0600 in a mode-0700 directory.
The WebUI database/password hash stays in its external Docker volume. Tokens,
browser profile/cookies, recovered databases and the private production baseline
remain outside the repo in /tmp; they are not commit candidates. The repository
contains only secret variable placeholders and private-file paths.

Production remains at f453ed161994c8131bf8d9ed7c43cc15914176cf with a clean worktree,
PID 5711/start ticks 2640 (started 2026-10-01 17:26:59 PDT). All 445 production data
files retain baseline SHA256, size and mtime, checked before and after this review
without updating production access times. Listeners remain 127.0.0.1:8096,
127.0.0.1:18096 and 127.0.0.1:3003; there are no 3001/3002 listeners. Their original
containers/volumes remain stopped, intact and restart=no.

No destination guard, custom cgroup, nftables/firewall mutation, Hindsight
integration, sudo execution, boot enablement, staging, commit or push occurred
during this review. Reboot persistence remains a reviewed proposal, not an
accepted runtime result.

## Exact files proposed for version control

This is the historical pre-promotion inventory. Current Git inventory also includes
check_reboot_acceptance.py, reboot-acceptance-plan.md and
acceptance/boot-promotion-verification.json. Nothing has been staged or committed.

```text
deploy/lab/README.md
deploy/lab/acceptance/01-lab-login.png
deploy/lab/acceptance/04-lab-sole-model.png
deploy/lab/acceptance/05-lab-first-chat.png
deploy/lab/acceptance/07-lab-resume-confirmed.png
deploy/lab/acceptance/08-lab-distinct-chat.png
deploy/lab/acceptance/09-lab-unavailable-sanitized.png
deploy/lab/acceptance/10-lab-restart-persistence.png
deploy/lab/acceptance/acceptance-evidence.json
deploy/lab/acceptance/retained-webui-final-audit.json
deploy/lab/acceptance/webui-final-inventory.json
deploy/lab/boot-persistence-review.md
deploy/lab/compose.boot.yml
deploy/lab/compose.webui.yml
deploy/lab/corvus-lab-api.service
deploy/lab/deployment.json
deploy/lab/ow2e-a-acceptance.md
deploy/lab/runtime-dependencies.json
deploy/lab/webui-bootstrap-result.json
```
