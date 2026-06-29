#!/bin/sh
set -eu

LOG_PATH="${1:-/tmp/wc2026-allow-docker-forward.log}"
NAS_PATH="${2:-/share/CACHEDEV1_DATA/Web/wc2026}"
LAN_CIDR="${3:-192.168.100.0/24}"

exec > "$LOG_PATH" 2>&1

export PATH="/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/docker/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/sbin:/opt/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:$PATH"

echo "STEP date"
date

echo "STEP app state"
cd "$NAS_PATH"
docker compose --env-file .env ps
docker port wc2026-frontend || true

FRONTEND_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wc2026-frontend)"
if [ -z "$FRONTEND_IP" ]; then
  echo "Could not determine wc2026-frontend container IP"
  exit 20
fi

echo "STEP frontend ip"
echo "$FRONTEND_IP"

add_rule() {
  chain="$1"
  if ! iptables -S "$chain" >/dev/null 2>&1; then
    echo "Chain $chain not found, skipping"
    return 0
  fi

  if iptables -C "$chain" -s "$LAN_CIDR" -d "$FRONTEND_IP" -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
    echo "Rule already exists in $chain"
  else
    iptables -I "$chain" 1 -s "$LAN_CIDR" -d "$FRONTEND_IP" -p tcp --dport 80 -j ACCEPT
    echo "Inserted rule in $chain: $LAN_CIDR -> $FRONTEND_IP:80"
  fi
}

echo "STEP insert forward allow rules"
add_rule SYSDOCKER-USER
add_rule DOCKER-USER

echo "STEP chain heads"
iptables -nvL SYSDOCKER-USER --line-numbers 2>/dev/null | sed -n '1,25p' || true
iptables -nvL DOCKER-USER --line-numbers 2>/dev/null | sed -n '1,25p' || true

echo "STEP local tests"
wget -S -O /dev/null -T 5 http://127.0.0.1:12302/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.250:12302/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.185:12302/ 2>&1 || true

echo "STEP done"
