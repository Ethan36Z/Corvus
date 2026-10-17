# Minimum Durable Corvus Lab Console

Canonical Linux URL: http://127.0.0.1:3003.

Prepared remote HTTPS configuration is documented in [https/README.md](https/README.md).
It is not deployed; keep the existing local Compose stack until separately authorized.

Admin: admin@corvus-lab.invalid. Read the password locally from the private
/home/ethan/.config/corvus-lab/admin-bootstrap.json file. Authentication signing
secret is separately retained in mode-0600 webui.env in the same directory.

Persistent data volume: corvus-lab-open-webui-data, external to Compose.
Lab canonical memory remains exclusively under /home/ethan/srv/data/corvus/lab.
The original 3001/3002 containers and volumes are separate and remain stopped.

For a manual start, verify the tag's image ID first:

```bash
docker image inspect corvus-open-webui:0.6.5-ow2d.1 --format '{{.Id}}'
```

Required ID: sha256:52c80cb880eb4482f12e6df2b0dec55326a57fdf94fabb3184b76b7afb918b1b.
If it differs, stop for review. Otherwise validate and start only this project:

```bash
docker compose --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.webui.yml \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.boot.yml config --quiet
docker compose --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.webui.yml \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.boot.yml \
  up -d --no-build --pull never open-webui
```

Manual WebUI restart (does not restart either API):

```bash
docker compose --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.webui.yml \
  -f /home/ethan/srv/apps/corvus-lab/deploy/lab/compose.boot.yml \
  restart open-webui
```

Boot promotion is complete: Lab API enabled; only Lab WebUI restart=unless-stopped.
The API and WebUI were not restarted by promotion. Controlled reboot product acceptance passed; firewall semantic persistence is deferred. OS-level cgroup/nftables destination hardening is deferred. Use ordinary
saved-chat text turns; the sealed Pipe's other reviewed limitations still apply.

Acceptance results and retained synthetic history: ow2e-a-acceptance.md.

## Boot persistence — product reboot acceptance passed

Use both Compose files for every start/recreation, as shown above. Docker's
unless-stopped policy preserves intentional manual stops across reboot. The
existing Lab API unit is enabled; its source snapshot is unchanged. Production,
3001/3002, shared model, Hindsight and firewall/cgroup configuration were not
modified. The operator-controlled reboot and real saved-chat browser reload passed
product acceptance. The strict reboot checker retains an unresolved runtime
firewall hash mismatch, explicitly deferred from OW2e-A by the operator.

See [reboot-acceptance-plan.md](reboot-acceptance-plan.md) for the exact manual
historical reboot procedure, durable baseline/checker and retained limitation.
See [ow2e-a-acceptance.md](ow2e-a-acceptance.md) for the final product result.
[boot-persistence-review.md](boot-persistence-review.md) retains the historical
approved proposal. No staging, commit or push has occurred.
