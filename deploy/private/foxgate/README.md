# Existing Production Corvus gateway recovery source

This directory preserves only the two **non-secret, Corvus-only** Nginx files
observed under `/home/ethan/srv/infrastructure/private-access/v2/nginx` at the
2026-10-23 source closeout. They are byte copies of the running configuration,
not a new gateway design. No Compose environment, credentials, Tunnel account
configuration or unrelated personal project routes are included.

| Setting | Existing value |
| --- | --- |
| Public Corvus host | corvus.foxluma.com |
| Gateway origin | 127.0.0.1:8093 |
| FoxGate Auth | 127.0.0.1:8094 |
| Corvus web upstream | 127.0.0.1:8097 |
| Nginx main config mount | /etc/nginx/nginx.conf (read-only) |
| Auth locations mount | /etc/nginx/foxgate/gated-locations.conf (read-only) |

External Auth source: `https://github.com/Ethan36Z/foxgate.git`, commit
`a8aea8661ef140bf588c6663b82f6de98bd95043` (contains deployed Auth source
`1009bba`). Existing pinned Auth image:
`sha256:2d7745847cb4f5875496830082bd9bcd5bbc5aa1d0c8733e18a07646d4772523`.
The existing Lab bundle in `deploy/lab/foxgate/` records the Nginx/Auth recipe;
it is a **different realm**, not a drop-in replacement for Production.

## Recovery boundary and procedure

1. Obtain the separately protected current private-access Compose/operator
   packet, independent private-realm password hash and HMAC secret, pinned
   images and Cloudflare Tunnel routing. These are intentionally outside Git.
   Retain existing files and permissions; do not create new accounts or keys
   merely to restore source. Never substitute Lab/Demo secrets or dump runtime
   environment/Compose values to a public log.
2. Review the two files here against that packet. Restore them only to the
   private-access Nginx config paths, keeping the existing mounts and permissions.
   Preserve `auth_request`, its internal verification endpoint, login throttle,
   default-host 404, downstream Authorization/Cookie handling and no alternate
   unauthenticated upstream. This closeout does not modernize forwarding,
   streaming or timeout behavior.
3. Before any separately authorized replacement, run the existing pinned Nginx
   `-t` syntax-check method from the Lab gateway README with these two readonly
   config mounts and networking disabled. Keep the private origin restricted to
   loopback. Preserve the existing Tunnel route to 8093; do not expose 8097,
   the API or a new origin directly.
4. Any future activation must check private-realm login, fail-closed Auth,
   application login, HTTPS and the existing rollback packet. Restore the prior
   two config files and prior gateway image if acceptance fails. Do not restart
   Lab, Demo, APIs, model or memory services to repair a gateway config.

This is source preservation, **not a complete gateway disaster-recovery pack**.
Cloudflare account routing, secret backups and exact historical web build
provenance remain separate operator responsibilities. No gateway changes or
new login acceptance were performed during source closeout. Lab's currently
accepted public route remains `https://lab-corvus.foxluma.com`.
