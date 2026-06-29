#!/bin/sh
set -u

LOG_PATH="${1:-/tmp/wc2026-port-capture.log}"
CLIENT_IP="${2:-192.168.100.26}"
APP_PORT="${3:-12302}"
PUBLIC_PORT="${4:-12026}"

exec > "$LOG_PATH" 2>&1

echo "STEP date"
date

echo "STEP tcpdump path"
command -v tcpdump || {
  echo "tcpdump not found"
  exit 0
}

echo "STEP capture start"
echo "client=$CLIENT_IP app_port=$APP_PORT public_port=$PUBLIC_PORT"

tcpdump -ni any -tt "host $CLIENT_IP and (tcp port $APP_PORT or tcp port $PUBLIC_PORT)" -c 40 &
TCPDUMP_PID=$!

sleep 15
kill "$TCPDUMP_PID" 2>/dev/null || true
wait "$TCPDUMP_PID" 2>/dev/null || true

echo "STEP capture done"
