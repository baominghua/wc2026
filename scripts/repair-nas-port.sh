#!/bin/sh
set -eu

NAS_PATH="${1:-/share/CACHEDEV1_DATA/Web/wc2026}"

export PATH="/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/docker/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/sbin:/opt/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:$PATH"

echo "STEP host"
hostname

echo "STEP docker"
command -v docker

echo "STEP project"
cd "$NAS_PATH"
pwd

echo "STEP env prepare"
if [ ! -f .env ]; then
  cp .env.nas.example .env
fi

echo "STEP env before"
grep '^APP_PORT=' .env || true
grep '^PROJECT_DIR=' .env || true
grep '^COMPOSE_PROJECT_NAME=' .env || true

echo "STEP set env"
if grep -q '^APP_PORT=' .env; then
  sed -i 's/^APP_PORT=.*/APP_PORT=12302/' .env
else
  printf '\nAPP_PORT=12302\n' >> .env
fi

if grep -q '^PROJECT_DIR=' .env; then
  sed -i 's#^PROJECT_DIR=.*#PROJECT_DIR=/share/CACHEDEV1_DATA/Web/wc2026#' .env
else
  printf '\nPROJECT_DIR=/share/CACHEDEV1_DATA/Web/wc2026\n' >> .env
fi

if grep -q '^COMPOSE_PROJECT_NAME=' .env; then
  sed -i 's/^COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=wc2026/' .env
else
  printf '\nCOMPOSE_PROJECT_NAME=wc2026\n' >> .env
fi

echo "STEP env after"
grep '^APP_PORT=' .env
grep '^PROJECT_DIR=' .env
grep '^COMPOSE_PROJECT_NAME=' .env

echo "STEP compose up"
docker compose --env-file .env up -d --build

echo "STEP compose ps"
docker compose --env-file .env ps

echo "STEP docker port"
docker port wc2026-frontend || true

echo "STEP listening"
netstat -tln 2>/dev/null | grep ':12302' || true
netstat -tln 2>/dev/null | grep ':12026' || true

echo "STEP local test 12302"
if command -v wget >/dev/null 2>&1; then
  wget -S -O /dev/null -T 8 http://127.0.0.1:12302/
else
  curl -I --max-time 8 http://127.0.0.1:12302/
fi

echo "STEP local test 12026"
if command -v wget >/dev/null 2>&1; then
  wget -S -O /dev/null -T 3 http://127.0.0.1:12026/ || true
else
  curl -I --max-time 3 http://127.0.0.1:12026/ || true
fi

echo "STEP done"
