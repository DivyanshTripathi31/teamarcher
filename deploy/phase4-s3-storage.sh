#!/usr/bin/env bash
# Run manually on EC2 as the sudo-capable ubuntu user:
#   bash /opt/teamarcher/deploy/phase4-s3-storage.sh <private-s3-bucket> [region]
#
# This configures only the private S3 bucket and region. It intentionally uses
# the instance role/default AWS provider chain; it never accepts, stores, or
# prints AWS access keys.
set -Eeuo pipefail

BUCKET="${1:?Usage: $0 <private-s3-bucket> [region]}"
REGION="${2:-ap-south-1}"
APP_ROOT="/opt/teamarcher"
BACKEND_DIR="$APP_ROOT/backend"
VENV="$BACKEND_DIR/.venv"
SERVICE_NAME="teamarcher-backend"
SERVICE_USER="teamarcher"
ENV_FILE="/etc/teamarcher/backend.env"

if [[ ! "$BUCKET" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ || ! "$REGION" =~ ^[a-z]{2}-[a-z]+-[0-9]+$ ]]; then
  echo "Bucket name or AWS region format is invalid." >&2
  exit 2
fi
if ! sudo -n true; then
  echo "Passwordless sudo is required; refusing to prompt interactively." >&2
  exit 1
fi
if ! sudo -n -u "$SERVICE_USER" test -x "$VENV/bin/python" || ! sudo -n -u "$SERVICE_USER" test -r "$ENV_FILE"; then
  echo "Phase 1/2 prerequisites are missing: service virtual environment or protected environment file." >&2
  exit 1
fi

# Never retain static credentials or a development endpoint in the production
# runtime file. This does not print existing values.
sudo -n sed -i \
  -e '/^S3_BUCKET=/d' \
  -e '/^AWS_REGION=/d' \
  -e '/^AWS_ACCESS_KEY_ID=/d' \
  -e '/^AWS_SECRET_ACCESS_KEY=/d' \
  -e '/^AWS_SESSION_TOKEN=/d' \
  -e '/^S3_ENDPOINT_URL=/d' \
  -e '/^S3_PUBLIC_ENDPOINT_URL=/d' \
  "$ENV_FILE"
printf 'S3_BUCKET=%s\nAWS_REGION=%s\n' "$BUCKET" "$REGION" | sudo -n tee -a "$ENV_FILE" >/dev/null
sudo -n chown root:"$SERVICE_USER" "$ENV_FILE"
sudo -n chmod 0640 "$ENV_FILE"

sudo -n systemctl restart "$SERVICE_NAME"

echo "Waiting for FastAPI readiness…"
ready=false
for _ in {1..20}; do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo "Backend did not become healthy within 20 seconds." >&2
  sudo -n systemctl --no-pager --full status "$SERVICE_NAME" >&2 || true
  exit 1
fi

echo "Verifying private-bucket PutObject/GetObject/DeleteObject through the instance role…"
verification_key="verification/phase4-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 8).txt"
sudo -n -u "$SERVICE_USER" env VERIFY_KEY="$verification_key" bash -c '
  set -Eeuo pipefail
  set -a
  . /etc/teamarcher/backend.env
  set +a
  cd /opt/teamarcher/backend
  exec /opt/teamarcher/backend/.venv/bin/python - <<"PY"
import os

for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
    if os.environ.get(name):
        raise SystemExit(f"Static AWS credential variable is set: {name}")

from app.storage import client

key = os.environ["VERIFY_KEY"]
body = b"teamarcher phase 4 storage verification"
s3 = client()
created = False
try:
    s3.put_object(Bucket=os.environ["S3_BUCKET"], Key=key, Body=body, ContentType="text/plain")
    created = True
    if s3.get_object(Bucket=os.environ["S3_BUCKET"], Key=key)["Body"].read() != body:
        raise RuntimeError("S3 verification object did not round-trip correctly")
finally:
    if created:
        s3.delete_object(Bucket=os.environ["S3_BUCKET"], Key=key)
PY
'

sudo -n systemctl is-active --quiet "$SERVICE_NAME"
echo "Phase 4 complete: private S3 storage is configured through the EC2 IAM role."
