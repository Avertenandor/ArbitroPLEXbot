#!/usr/bin/env bash
# MCP-MARKER:CREATE:ROTATE_DB_PASSWORD_SCRIPT
# MCP-PROVIDES: rotate_db_password()
# MCP-SUMMARY: Safe Postgres password rotation for ArbitroPLEXbot (no secret output)

set -euo pipefail

COMPOSE_FILE="docker-compose.python.yml"
ENV_FILE=".env"

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: $COMPOSE_FILE not found. Run from the project root (e.g. /opt/arbitragebot)." >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Refusing to proceed." >&2
  exit 1
fi

compose() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" "$@"
  else
    docker compose -f "$COMPOSE_FILE" "$@"
  fi
}

postgres_cid="$(compose ps -q postgres | head -n 1)"
if [ -z "$postgres_cid" ]; then
  echo "ERROR: postgres container not found (compose ps -q postgres empty)." >&2
  exit 1
fi

DBUSER="$(docker exec "$postgres_cid" printenv POSTGRES_USER 2>/dev/null || true)"
DBNAME="$(docker exec "$postgres_cid" printenv POSTGRES_DB 2>/dev/null || true)"
DBUSER="${DBUSER:-postgres}"
DBNAME="${DBNAME:-postgres}"

echo "db_user=$DBUSER"
echo "db_name=$DBNAME"

gen_pass() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets; print(secrets.token_hex(24))'
  elif command -v python >/dev/null 2>&1; then
    python -c 'import secrets; print(secrets.token_hex(24))'
  elif command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    echo "ERROR: Need python3 or openssl to generate a password." >&2
    exit 1
  fi
}

NEWPASS="$(gen_pass)"

# Rotate role password (do NOT print secret)
printf 'ALTER ROLE "%s" WITH PASSWORD $$%s$$;\n' "$DBUSER" "$NEWPASS" \
  | docker exec -i "$postgres_cid" psql -U "$DBUSER" -d "$DBNAME" >/dev/null

ts="$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$ENV_FILE.bak.$ts"

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

ENV_FILE="$ENV_FILE" dbuser="$DBUSER" newpass="$NEWPASS" "$PYTHON_BIN" - <<'PY'
import os
import re

path = os.environ.get('ENV_FILE', '.env')
dbuser = os.environ['dbuser']
newpass = os.environ['newpass']

with open(path, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

out = []
updated = False
for line in lines:
    if line.startswith('DATABASE_URL='):
        val = line.split('=', 1)[1].strip()
        # Replace only the first occurrence of //user:pass@
        pattern = r'//%s:[^@]*@' % re.escape(dbuser)
        repl = '//%s:%s@' % (dbuser, newpass)
        new_val, n = re.subn(pattern, repl, val, count=1)
        if n:
            val = new_val
            updated = True
        out.append('DATABASE_URL=' + val)
    else:
        out.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')

print('database_url_updated=' + ('1' if updated else '0'))
for line in out:
    if line.startswith('DATABASE_URL='):
        masked = re.sub(r'(://[^:]+:)[^@]*(@)', r'\1***MASKED***\2', line)
        print(masked)
PY

# IMPORTANT: restart does NOT reread .env; recreate containers to apply new DATABASE_URL.
compose up -d --no-deps --force-recreate bot scheduler worker

echo "Done. If bot still errors, check logs:" \
  "compose logs --tail 200 bot" \
  "compose logs --tail 200 worker" \
  "compose logs --tail 200 scheduler"
