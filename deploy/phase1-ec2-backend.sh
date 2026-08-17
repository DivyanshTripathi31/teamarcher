#!/usr/bin/env bash
# Run manually on the EC2 host as a sudo-capable user:
#   bash /opt/teamarcher/deploy/phase1-ec2-backend.sh ec2-public-dns-name
#
# This intentionally stops at a health-only backend foundation. PostgreSQL,
# S3/IAM, HTTPS, DNS, and production application accounts are separate phases.
set -Eeuo pipefail

PUBLIC_HOST="${1:?Usage: $0 <EC2 public DNS name or public IP>}"
APP_ROOT="/opt/teamarcher"
BACKEND_DIR="$APP_ROOT/backend"
VENV="$BACKEND_DIR/.venv"
SERVICE_NAME="teamarcher-backend"
ENV_DIR="/etc/teamarcher"
ENV_FILE="$ENV_DIR/backend.env"
SERVICE_USER="teamarcher"

if [[ ! -f "$BACKEND_DIR/requirements.txt" || ! -f "$APP_ROOT/deploy/systemd/$SERVICE_NAME.service" ]]; then
  echo "Expected Team Archer checkout is not present at $APP_ROOT." >&2
  exit 1
fi

sudo -v

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  sudo useradd --system --home-dir /var/lib/teamarcher --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# Keep application source root-owned. Only the virtual environment is writable
# by the service account for dependency installation.
sudo chown -R root:"$SERVICE_USER" "$APP_ROOT"
sudo chmod -R g+rX "$APP_ROOT"
if [[ ! -x "$VENV/bin/python" ]]; then
  sudo python3 -m venv "$VENV"
fi
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$VENV"
sudo -u "$SERVICE_USER" "$VENV/bin/pip" install --upgrade pip
sudo -u "$SERVICE_USER" "$VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

sudo install -d -o root -g "$SERVICE_USER" -m 0750 "$ENV_DIR"
sudo install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 /var/lib/teamarcher

# Never overwrite a real existing environment file. The first run generates the
# JWT locally on EC2 and leaves database/object-storage unset for this phase.
if [[ ! -f "$ENV_FILE" ]]; then
  jwt_secret="$(openssl rand -hex 32)"
  sudo tee "$ENV_FILE" >/dev/null <<EOF
JWT_SECRET=$jwt_secret
JWT_EXPIRE_MINUTES=480
CORS_ORIGINS=https://divyanshtripathi31.github.io
SEED_INITIAL_USERS=false
INITIAL_USER_PASSWORDS_JSON={}
MAX_UPLOAD_MB=50
EOF
  unset jwt_secret
fi
sudo chown root:"$SERVICE_USER" "$ENV_FILE"
sudo chmod 0640 "$ENV_FILE"

sudo install -o root -g root -m 0644 "$APP_ROOT/deploy/systemd/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

sudo install -o root -g root -m 0644 "$APP_ROOT/deploy/nginx/teamarcher-backend.conf" /etc/nginx/sites-available/teamarcher-backend
sudo ln -sfn /etc/nginx/sites-available/teamarcher-backend /etc/nginx/sites-enabled/teamarcher-backend

# This host received the stock Nginx site during the Phase 1 package install.
# Remove only that known default symlink so Team Archer is the port-80 server.
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "== Service checks =="
sudo systemctl is-active --quiet "$SERVICE_NAME"
sudo systemctl is-enabled --quiet "$SERVICE_NAME"
sudo systemctl is-active --quiet nginx
[[ "$(sudo systemctl show -p User --value "$SERVICE_NAME")" == "$SERVICE_USER" ]]

echo "== Health checks =="
curl --fail --silent --show-error http://127.0.0.1:8000/health
echo
curl --fail --silent --show-error -H "Host: $PUBLIC_HOST" http://127.0.0.1/health
echo
curl --fail --silent --show-error "http://$PUBLIC_HOST/health"
echo

echo "== Listener check =="
sudo ss -ltnp '( sport = :8000 )'
echo "Phase 1 complete: http://$PUBLIC_HOST/health"
