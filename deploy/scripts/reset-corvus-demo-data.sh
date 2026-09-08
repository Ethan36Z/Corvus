#!/usr/bin/env bash
set -euo pipefail
umask 077

CORVUS="/home/ethan/srv/apps/small-vram-companion"
PY="$CORVUS/.venv/bin/python"

EXPECTED_DEMO="/home/ethan/srv/data/corvus/demo"
EXPECTED_PRIVATE="/home/ethan/srv/data/corvus/private"

DEMO_DATA="$EXPECTED_DEMO"
PRIVATE_DATA="$EXPECTED_PRIVATE"
BACKUP_ROOT="/home/ethan/srv/backups/corvus-demo-resets"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$CORVUS"

echo "reset_started_utc=$TS"

if [ "$DEMO_DATA" != "$EXPECTED_DEMO" ]; then
  echo "ERROR: DEMO_DATA does not match exact allowed path."
  exit 1
fi

if [ "$PRIVATE_DATA" != "$EXPECTED_PRIVATE" ]; then
  echo "ERROR: PRIVATE_DATA does not match exact expected private path."
  exit 1
fi

if [ "$DEMO_DATA" = "$PRIVATE_DATA" ]; then
  echo "ERROR: demo and private paths are identical."
  exit 1
fi

if [ ! -d "$DEMO_DATA" ]; then
  echo "ERROR: demo data directory missing: $DEMO_DATA"
  exit 1
fi

if [ ! -d "$PRIVATE_DATA" ]; then
  echo "ERROR: private data directory missing: $PRIVATE_DATA"
  exit 1
fi

if [ -L "$DEMO_DATA" ] || [ -L "$PRIVATE_DATA" ]; then
  echo "ERROR: refusing to operate on symlinked data directories."
  exit 1
fi

DEMO_REAL="$(realpath -e "$DEMO_DATA")"
PRIVATE_REAL="$(realpath -e "$PRIVATE_DATA")"

if [ "$DEMO_REAL" != "$EXPECTED_DEMO" ]; then
  echo "ERROR: resolved demo path mismatch: $DEMO_REAL"
  exit 1
fi

if [ "$PRIVATE_REAL" != "$EXPECTED_PRIVATE" ]; then
  echo "ERROR: resolved private path mismatch: $PRIVATE_REAL"
  exit 1
fi

if [ "$DEMO_REAL" = "$PRIVATE_REAL" ]; then
  echo "ERROR: resolved demo/private paths are identical."
  exit 1
fi

PRIVATE_BEFORE="$("$PY" - <<'PY'
import sqlite3

db = "/home/ethan/srv/data/corvus/private/corvus.db"

with sqlite3.connect(db) as conn:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit("private integrity failed")
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

print(count)
PY
)"

DEMO_BEFORE="$("$PY" - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/home/ethan/srv/data/corvus/demo/corvus.db")

if not db.exists():
    print("missing")
else:
    with sqlite3.connect(db) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit("demo integrity failed")
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'").fetchone()
        if row is None:
            print("no_messages_table")
        else:
            print(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
PY
)"

echo "private_messages_before=$PRIVATE_BEFORE"
echo "demo_messages_before=$DEMO_BEFORE"

install -d -m 700 "$BACKUP_ROOT"
install -d -m 700 "$BACKUP_ROOT/$TS"

if find "$DEMO_DATA" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  tar \
    -C "$DEMO_DATA" \
    --exclude='./attachments' \
    --exclude='./attachments/**' \
    -czf "$BACKUP_ROOT/$TS/demo-data-before-reset.tgz" \
    .
  echo "demo_backup=$BACKUP_ROOT/$TS/demo-data-before-reset.tgz"
  echo "demo_backup_excludes_raw_attachments=YES"
else
  echo "demo_backup=SKIPPED_EMPTY_DIR"
fi

echo "stopping_corvus_demo_api=YES"
systemctl stop corvus-demo-api.service

echo "clearing_demo_data_only=$DEMO_DATA"
find "$DEMO_DATA" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

chown ethan:ethan "$DEMO_DATA"
chmod 700 "$DEMO_DATA"

echo "initializing_demo_sqlite_schema=YES"
runuser -u ethan -- env PYTHONPATH="$CORVUS" CORVUS_DATA_DIR="$DEMO_DATA" "$PY" -m memory.store

chown -R ethan:ethan "$DEMO_DATA"
chmod 700 "$DEMO_DATA"

echo "starting_corvus_demo_api=YES"
systemctl start corvus-demo-api.service

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8098/api/health >/tmp/corvus-demo-reset-health.json 2>/dev/null; then
    echo "demo_health_ready_attempt=$i"
    cat /tmp/corvus-demo-reset-health.json
    echo
    break
  fi
  echo "waiting_for_demo_api=$i"
  sleep 1
done

curl -fsS http://127.0.0.1:8098/api/health >/tmp/corvus-demo-reset-health.json

VERIFY="$("$PY" - <<'PY'
import sqlite3
from pathlib import Path

private_db = Path("/home/ethan/srv/data/corvus/private/corvus.db")
demo_db = Path("/home/ethan/srv/data/corvus/demo/corvus.db")

with sqlite3.connect(private_db) as conn:
    private_integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    private_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

with sqlite3.connect(demo_db) as conn:
    demo_integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    demo_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

print(f"private_integrity={private_integrity}")
print(f"private_messages_after={private_messages}")
print(f"demo_integrity={demo_integrity}")
print(f"demo_messages_after={demo_messages}")

if private_integrity != "ok":
    raise SystemExit("private integrity failed after reset")
if demo_integrity != "ok":
    raise SystemExit("demo integrity failed after reset")
if demo_messages != 0:
    raise SystemExit(f"demo should be empty after reset, got {demo_messages}")
PY
)"

echo "$VERIFY"

PRIVATE_AFTER="$(printf '%s\n' "$VERIFY" | awk -F= '/private_messages_after=/{print $2}')"

if [ "$PRIVATE_BEFORE" != "$PRIVATE_AFTER" ]; then
  echo "ERROR: private message count changed: before=$PRIVATE_BEFORE after=$PRIVATE_AFTER"
  exit 1
fi

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf -- {} +

echo "private_unchanged=YES"
echo "demo_reset_complete=YES"
