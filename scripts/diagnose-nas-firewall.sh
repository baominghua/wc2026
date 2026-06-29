#!/bin/sh
set -u

LOG_PATH="${1:-/tmp/wc2026-firewall-diag.log}"
NAS_PATH="${2:-/share/CACHEDEV1_DATA/Web/wc2026}"

exec > "$LOG_PATH" 2>&1

export PATH="/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/docker/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/sbin:/opt/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:$PATH"

echo "STEP date"
date

echo "STEP host"
hostname

echo "STEP addresses"
ip -4 addr show 2>/dev/null || ifconfig 2>/dev/null || true

echo "STEP routes"
ip route 2>/dev/null || route -n 2>/dev/null || true

echo "STEP docker app"
cd "$NAS_PATH" || exit 11
grep '^APP_PORT=' .env || true
docker compose --env-file .env ps || true
docker port wc2026-frontend || true
docker inspect wc2026-frontend --format '{{json .NetworkSettings.Ports}}' 2>/dev/null || true

echo "STEP listening"
netstat -tlnp 2>/dev/null | grep ':12302' || true
ss -ltnp 2>/dev/null | grep ':12302' || true

echo "STEP iptables filter summary"
iptables -nvL 2>/dev/null || true

echo "STEP iptables filter rules"
iptables -S 2>/dev/null || true

echo "STEP iptables nat summary"
iptables -t nat -nvL 2>/dev/null || true

echo "STEP iptables nat rules"
iptables -t nat -S 2>/dev/null || true

echo "STEP iptables mangle rules"
iptables -t mangle -S 2>/dev/null || true

echo "STEP nft ruleset"
nft list ruleset 2>/dev/null || true

echo "STEP qnap firewall files"
find /etc/config /mnt/HDA_ROOT/.config -maxdepth 2 -iname '*fire*' -o -iname '*qufire*' 2>/dev/null || true

echo "STEP possible qnap firewall config"
for f in /etc/config/QuFirewall.conf /etc/config/qufirewall.conf /etc/config/uLinux.conf; do
  if [ -f "$f" ]; then
    echo "--- $f ---"
    sed -n '1,220p' "$f" 2>/dev/null || true
  fi
done

echo "STEP sysctl"
sysctl net.ipv4.ip_forward 2>/dev/null || true
sysctl net.bridge.bridge-nf-call-iptables 2>/dev/null || true

echo "STEP local tests"
wget -S -O /dev/null -T 5 http://127.0.0.1:12302/ 2>&1 || curl -I --max-time 5 http://127.0.0.1:12302/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.250:12302/ 2>&1 || curl -I --max-time 5 http://192.168.100.250:12302/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.185:12302/ 2>&1 || curl -I --max-time 5 http://192.168.100.185:12302/ 2>&1 || true

echo "STEP done"
