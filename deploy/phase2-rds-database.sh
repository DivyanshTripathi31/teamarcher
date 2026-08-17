#!/usr/bin/env bash
# Run manually on the EC2 host as the sudo-capable ubuntu user:
#   bash /opt/teamarcher/deploy/phase2-rds-database.sh <rds-endpoint> [database]
#
# This script never prints, stores in Git, or otherwise exports a database
# password. It uses a temporary, private PGPASSFILE only while Alembic runs.
# It deliberately does not touch S3, AWS IAM, DNS, TLS termination, or ports.
set -Eeuo pipefail

RDS_HOST="${1:?Usage: $0 <rds-endpoint> [database]}"
DATABASE_NAME="${2:-teamarcher}"
RDS_PORT="5432"
ADMIN_ROLE="teamarcher_admin"
APP_ROLE="teamarcher_app"
APP_ROOT="/opt/teamarcher"
BACKEND_DIR="$APP_ROOT/backend"
VENV="$BACKEND_DIR/.venv"
SERVICE_NAME="teamarcher-backend"
SERVICE_USER="teamarcher"
ENV_FILE="/etc/teamarcher/backend.env"

if [[ ! "$RDS_HOST" =~ ^[A-Za-z0-9.-]+$ || ! "$DATABASE_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "RDS host or database name contains unsupported characters." >&2
  exit 2
fi
if ! sudo -n true; then
  echo "Passwordless sudo is required; refusing to prompt interactively." >&2
  exit 1
fi
if ! sudo -n -u "$SERVICE_USER" test -x "$VENV/bin/python" || ! sudo -n -u "$SERVICE_USER" test -x "$VENV/bin/alembic"; then
  echo "Phase 1 is incomplete: the $SERVICE_USER account cannot execute the expected virtual-environment binaries." >&2
  exit 1
fi
# The environment file is deliberately root-owned and group-readable only by
# the service account. Check it through non-interactive sudo, never by the
# unprivileged invoking user and never by weakening its permissions.
if ! sudo -n -u "$SERVICE_USER" test -f "$ENV_FILE" || ! sudo -n -u "$SERVICE_USER" test -r "$ENV_FILE"; then
  echo "Phase 1 is incomplete: $ENV_FILE is missing or unreadable by $SERVICE_USER." >&2
  exit 1
fi
if ! command -v psql >/dev/null 2>&1; then
  echo "PostgreSQL client (psql) is required; install it before running Phase 2." >&2
  exit 1
fi

read -r -s -p "Password for ${ADMIN_ROLE} on RDS: " admin_password
echo
if [[ -z "$admin_password" ]]; then
  echo "No password supplied; nothing was changed." >&2
  exit 1
fi

admin_dsn="postgresql://${ADMIN_ROLE}@${RDS_HOST}:${RDS_PORT}/${DATABASE_NAME}?sslmode=require"
local_pgpass="$(mktemp)"
service_pgpass="/var/lib/teamarcher/.phase2-rds-pgpass.$$"
app_password=""
seed_file=""
service_seed_file=""
cleanup() {
  unset admin_password app_password
  rm -f "$local_pgpass"
  sudo -n rm -f "$service_pgpass" 2>/dev/null || true
  rm -f "$seed_file"
  [[ -z "$service_seed_file" ]] || sudo -n rm -f "$service_seed_file" 2>/dev/null || true
}
trap cleanup EXIT
chmod 0600 "$local_pgpass"

admin_psql() {
  PGPASSWORD="$admin_password" PGSSLMODE=require psql --no-psqlrc --set=ON_ERROR_STOP=1 "$admin_dsn" "$@"
}

echo "Checking the TLS database connection…"
[[ "$(admin_psql -Atqc "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")" == "t" ]] || {
  echo "The database session is not using TLS; refusing to continue." >&2
  exit 1
}

schema_state="$(admin_psql -Atqc "SELECT CASE WHEN to_regclass('public.alembic_version') IS NOT NULL THEN 'versioned' WHEN to_regclass('public.users') IS NOT NULL THEN 'unversioned' ELSE 'empty' END")"
if [[ "$schema_state" == "unversioned" ]]; then
  echo "Existing unversioned application tables found. Refusing to stamp or overwrite them automatically." >&2
  echo "Back up and reconcile that schema with Alembic before rerunning this script." >&2
  exit 1
fi

app_role_exists="$(admin_psql -Atqc "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${APP_ROLE}')")"
app_url_configured=false
if sudo -n grep -q '^DATABASE_URL=' "$ENV_FILE"; then
  app_url_configured=true
fi

if [[ "$app_url_configured" == true && "$app_role_exists" == "f" ]]; then
  echo "DATABASE_URL already exists but ${APP_ROLE} does not. Refusing to replace credentials automatically." >&2
  exit 1
fi

# A prior attempt can create the application role before a later migration
# step fails. When no application URL has ever been stored, safely retain that
# role and set a fresh random password for the first managed configuration.
if [[ "$app_url_configured" == false ]]; then
  app_password="$(openssl rand -hex 32)"
  if [[ "$app_role_exists" == "f" ]]; then
    echo "Creating the least-privilege application role…"
    admin_psql -v app_password="$app_password" <<'SQL'
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L',
  'teamarcher_app', :'app_password'
) WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'teamarcher_app')
\gexec
SQL
  else
    echo "Reusing the existing application role with a fresh managed credential…"
    admin_psql -v app_password="$app_password" <<'SQL'
SELECT format(
  'ALTER ROLE %I PASSWORD %L',
  'teamarcher_app', :'app_password'
)
\gexec
SQL
  fi
fi

# Provide the migration process an ephemeral password file rather than placing
# the administrative password in command arguments or /etc/teamarcher.
printf '%s:%s:%s:%s:%s\n' "$RDS_HOST" "$RDS_PORT" "$DATABASE_NAME" "$ADMIN_ROLE" "$admin_password" >"$local_pgpass"
sudo -n install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0600 "$local_pgpass" "$service_pgpass"

echo "Running Alembic migrations as ${ADMIN_ROLE} over TLS…"
sudo -n -u "$SERVICE_USER" env \
  PGPASSFILE="$service_pgpass" \
  DATABASE_URL="postgresql+psycopg://${ADMIN_ROLE}@${RDS_HOST}:${RDS_PORT}/${DATABASE_NAME}?sslmode=require" \
  DATABASE_AUTO_CREATE=false \
  bash -c 'cd "$1" && exec "$2" -c alembic.ini upgrade head' _ "$BACKEND_DIR" "$VENV/bin/alembic"

echo "Applying application role grants…"
admin_psql <<'SQL'
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), 'teamarcher_app')
\gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO teamarcher_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO teamarcher_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO teamarcher_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO teamarcher_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO teamarcher_app;
SQL

if [[ "$app_url_configured" == false ]]; then
  app_url="postgresql+psycopg://${APP_ROLE}:${app_password}@${RDS_HOST}:${RDS_PORT}/${DATABASE_NAME}?sslmode=require"
  sudo -n tee -a "$ENV_FILE" >/dev/null <<EOF
DATABASE_URL=$app_url
EOF
  unset app_url app_password
fi
# Production schema changes are exclusively Alembic-managed, never made by a
# web-process startup race.
sudo -n sed -i '/^DATABASE_AUTO_CREATE=/d' "$ENV_FILE"
printf 'DATABASE_AUTO_CREATE=false\n' | sudo -n tee -a "$ENV_FILE" >/dev/null
sudo -n chown root:"$SERVICE_USER" "$ENV_FILE"
sudo -n chmod 0640 "$ENV_FILE"

read -r -p "Seed the five intended initial Team Archer accounts now? [y/N] " seed_accounts
if [[ "$seed_accounts" =~ ^[Yy]$ ]]; then
  seed_file="$(mktemp)"
  service_seed_file="/var/lib/teamarcher/.phase2-seed.$$"
  chmod 0600 "$seed_file"
  python3 - "$seed_file" <<'PY'
import json
import os
import sys
from getpass import getpass

accounts = [
    "DIVYANSH TRIPATHI",
    "MEHARDEEP SINGH",
    "VIDIT GUPTA",
    "LAVISH GAMBHIR",
    "SUKHPAL SINGH",
]
passwords = {}
for account in accounts:
    password = getpass(f"Initial password for {account}: ")
    if not password:
        raise SystemExit("Empty initial passwords are not allowed.")
    passwords[account] = password
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(passwords, handle)
PY
  sudo -n install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0600 "$seed_file" "$service_seed_file"
  sudo -n -u "$SERVICE_USER" bash -c 'cd "$1" || exit 1; set -a; . /etc/teamarcher/backend.env; export SEED_INITIAL_USERS=true INITIAL_USER_PASSWORDS_JSON="$(cat "$2")"; exec "$3" -c "from app.bootstrap import bootstrap_database; bootstrap_database()"' _ "$BACKEND_DIR" "$service_seed_file" "$VENV/bin/python"
  rm -f "$seed_file"
  seed_file=""
  sudo -n rm -f "$service_seed_file"
  service_seed_file=""
else
  echo "Initial accounts were not seeded. The application’s site-content bootstrap will still run."
fi

sudo -n systemctl restart "$SERVICE_NAME"
sudo -n systemctl is-active --quiet "$SERVICE_NAME"
sudo -n systemctl is-active --quiet nginx

echo "Verifying the application role can query RDS…"
sudo -n -u "$SERVICE_USER" bash -c 'set -a; . /etc/teamarcher/backend.env; exec "$1" -c "from sqlalchemy import text; from app.database import engine; connection = engine.connect(); print(connection.scalar(text(\"SELECT current_user\"))); connection.close()"' _ "$VENV/bin/python"
echo "Verifying service and reverse proxy…"
curl --fail --silent --show-error http://127.0.0.1:8000/health
echo
curl --fail --silent --show-error http://127.0.0.1/api/site-content >/dev/null
echo "Database-backed API query succeeded."
echo "Phase 2 complete. The application remains bound to 127.0.0.1:8000."
