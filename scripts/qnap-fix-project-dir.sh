#!/bin/sh
set -eu

BASE_DIR="${1:-/share/CACHEDEV1_DATA/Web/wc2026}"

echo "Checking WC2026 project under: $BASE_DIR"

if [ ! -d "$BASE_DIR" ]; then
  echo "ERROR: Base directory does not exist: $BASE_DIR"
  echo "Create it or extract the package there first."
  exit 1
fi

find_project_dir() {
  if [ -d "$BASE_DIR/backend" ] && [ -d "$BASE_DIR/frontend" ]; then
    echo "$BASE_DIR"
    return 0
  fi

  for candidate in "$BASE_DIR"/*; do
    if [ -d "$candidate/backend" ] && [ -d "$candidate/frontend" ]; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

PROJECT_DIR="$(find_project_dir || true)"

if [ -z "$PROJECT_DIR" ]; then
  echo "ERROR: Could not find backend/ and frontend/ under $BASE_DIR"
  echo "Current contents:"
  ls -la "$BASE_DIR"
  echo ""
  echo "Expected one of these layouts:"
  echo "  $BASE_DIR/backend"
  echo "  $BASE_DIR/frontend"
  echo "or:"
  echo "  $BASE_DIR/<one-subfolder>/backend"
  echo "  $BASE_DIR/<one-subfolder>/frontend"
  exit 1
fi

echo "Found project directory: $PROJECT_DIR"

if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
  if [ -f "$BASE_DIR/docker-compose.yml" ]; then
    cp "$BASE_DIR/docker-compose.yml" "$PROJECT_DIR/docker-compose.yml"
    echo "Copied docker-compose.yml into $PROJECT_DIR"
  else
    echo "ERROR: docker-compose.yml not found in $PROJECT_DIR or $BASE_DIR"
    exit 1
  fi
fi

ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$PROJECT_DIR/.env.nas.example" ] && [ ! -f "$ENV_FILE" ]; then
  cp "$PROJECT_DIR/.env.nas.example" "$ENV_FILE"
fi
if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

if grep -q '^PROJECT_DIR=' "$ENV_FILE"; then
  sed -i "s|^PROJECT_DIR=.*|PROJECT_DIR=$PROJECT_DIR|" "$ENV_FILE"
else
  printf '\nPROJECT_DIR=%s\n' "$PROJECT_DIR" >> "$ENV_FILE"
fi

if grep -q '^APP_PORT=' "$ENV_FILE"; then
  true
else
  printf 'APP_PORT=2026\n' >> "$ENV_FILE"
fi

echo ""
echo "Fixed .env:"
grep -E '^(PROJECT_DIR|APP_PORT|LIVE_SYNC_ENABLED|LIVE_SYNC_INTERVAL_SECONDS|LIVE_FEED_STALE_SECONDS)=' "$ENV_FILE" || true
echo ""
echo "Next command:"
echo "  cd \"$PROJECT_DIR\" && docker compose --env-file .env up -d --build"
