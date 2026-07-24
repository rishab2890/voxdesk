#!/usr/bin/env bash
# One-command VoxDesk backend deploy for a VPS running alongside Dograh.
#
#   bash scripts/vps_setup.sh
#
# Writes a git-ignored .env (secrets from .env.secrets if present, else
# auto-generated), then builds and starts the backend stack on port 8080.
# Idempotent: re-run any time to apply changes or restart.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env"
SECRETS_FILE=".env.secrets"

gen() { openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-48; }

if [ ! -f "$ENV_FILE" ]; then
  echo "→ No .env found; creating one."

  # Prefer pre-seeded secrets (.env.secrets), else generate fresh ones.
  if [ -f "$SECRETS_FILE" ]; then
    echo "→ Using secrets from $SECRETS_FILE"
    # shellcheck disable=SC1090
    . "$SECRETS_FILE"
  fi
  JWT_SECRET="${JWT_SECRET:-$(gen)}"
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(gen)}"

  cp .env.example "$ENV_FILE"
  # Overwrite the placeholder secret lines with real values.
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "$ENV_FILE"
  # POSTGRES_PASSWORD drives both the DB and DATABASE_URL via compose.
  if grep -q '^POSTGRES_PASSWORD=' "$ENV_FILE"; then
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "$ENV_FILE"
  else
    echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" >> "$ENV_FILE"
  fi
  echo "✓ Wrote $ENV_FILE (secrets included). Retrieve later with: grep -E 'JWT_SECRET|POSTGRES_PASSWORD' $ENV_FILE"
else
  echo "→ Existing .env kept (delete it to regenerate secrets)."
fi

echo "→ Building and starting the backend stack…"
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d --build

echo "→ Waiting for the API to become healthy…"
for _ in $(seq 1 30); do
  if curl -fs http://localhost:8080/health >/dev/null 2>&1; then
    echo "✓ VoxDesk API is live on http://$(hostname -I | awk '{print $1}'):8080/health"
    exit 0
  fi
  sleep 3
done
echo "✗ API did not report healthy in time. Check logs: docker compose logs api" >&2
exit 1
