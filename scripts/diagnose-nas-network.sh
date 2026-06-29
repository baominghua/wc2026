#!/bin/sh
set -u

LOG_PATH="${1:-/tmp/wc2026-network-diag.log}"
NAS_PATH="${2:-/share/CACHEDEV1_DATA/Web/wc2026}"

exec > "$LOG_PATH" 2>&1

export PATH="/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/docker/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/sbin:/opt/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:$PATH"

echo "STEP date"
date

echo "STEP host"
hostname
hostname -I 2>/dev/null || true

echo "STEP addresses"
ip -4 addr show 2>/dev/null || ifconfig 2>/dev/null || true

echo "STEP routes"
ip route 2>/dev/null || route -n 2>/dev/null || true

echo "STEP project"
cd "$NAS_PATH" || exit 11
pwd

echo "STEP env"
grep '^APP_PORT=' .env || true
grep '^PROJECT_DIR=' .env || true
grep '^COMPOSE_PROJECT_NAME=' .env || true

echo "STEP compose ps"
docker compose --env-file .env ps || true

echo "STEP docker ps"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true

echo "STEP docker port"
docker port wc2026-frontend || true

echo "STEP listening"
netstat -tlnp 2>/dev/null | grep ':12302' || true
netstat -tlnp 2>/dev/null | grep ':12026' || true
ss -ltnp 2>/dev/null | grep ':12302' || true
ss -ltnp 2>/dev/null | grep ':12026' || true

echo "STEP local test 12302"
wget -S -O /dev/null -T 5 http://127.0.0.1:12302/ 2>&1 || curl -I --max-time 5 http://127.0.0.1:12302/ 2>&1 || true

echo "STEP local test 12026"
wget -S -O /dev/null -T 3 http://127.0.0.1:12026/ 2>&1 || curl -I --max-time 3 http://127.0.0.1:12026/ 2>&1 || true

echo "STEP done"
