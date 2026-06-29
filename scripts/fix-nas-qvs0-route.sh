#!/bin/sh
set -u

LOG_PATH="${1:-/tmp/wc2026-fix-qvs0-route.log}"
CLIENT_IP="${2:-192.168.100.26}"
APP_PORT="${3:-12302}"

exec > "$LOG_PATH" 2>&1

echo "STEP date"
date

echo "STEP host"
hostname
id

echo "STEP routes before"
ip route show

echo "STEP route to client before"
ip route get "$CLIENT_IP" || true

echo "STEP qvs interfaces before"
(ip -4 addr show qvs0 || true)
(ip -4 addr show qvs2 || true)

echo "STEP delete stale qvs0 same-subnet route"
ip route del 192.168.100.0/24 dev qvs0 2>/dev/null && echo "deleted qvs0 route" || echo "qvs0 route was already absent or could not be deleted"
ip route flush cache 2>/dev/null || true

echo "STEP routes after"
ip route show

echo "STEP route to client after"
ip route get "$CLIENT_IP" || true

echo "STEP local NAS tests"
if command -v wget >/dev/null 2>&1; then
  wget -S -O /dev/null -T 8 "http://127.0.0.1:$APP_PORT/tournament" 2>&1 || true
  wget -S -O /dev/null -T 8 "http://192.168.100.250:$APP_PORT/tournament" 2>&1 || true
else
  curl -I --max-time 8 "http://127.0.0.1:$APP_PORT/tournament" 2>&1 || true
  curl -I --max-time 8 "http://192.168.100.250:$APP_PORT/tournament" 2>&1 || true
fi

echo "STEP done"
