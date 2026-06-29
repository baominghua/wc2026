#!/bin/sh
set -eu

LOG_PATH="${1:-/tmp/wc2026-allow-lan.log}"
LAN_CIDR="${2:-192.168.100.0/24}"
APP_PORT="${3:-12302}"

exec > "$LOG_PATH" 2>&1

echo "STEP date"
date

echo "STEP current top QUFIREWALL"
iptables -nvL QUFIREWALL --line-numbers 2>/dev/null | sed -n '1,35p' || true

echo "STEP allow LAN to app port"
if iptables -C QUFIREWALL -s "$LAN_CIDR" -p tcp --dport "$APP_PORT" -j ACCEPT 2>/dev/null; then
  echo "Rule already present: $LAN_CIDR tcp/$APP_PORT"
else
  iptables -I QUFIREWALL 1 -s "$LAN_CIDR" -p tcp --dport "$APP_PORT" -j ACCEPT
  echo "Inserted rule: $LAN_CIDR tcp/$APP_PORT"
fi

echo "STEP updated top QUFIREWALL"
iptables -nvL QUFIREWALL --line-numbers 2>/dev/null | sed -n '1,35p' || true

echo "STEP local app tests"
wget -S -O /dev/null -T 5 http://127.0.0.1:"$APP_PORT"/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.250:"$APP_PORT"/ 2>&1 || true
wget -S -O /dev/null -T 5 http://192.168.100.185:"$APP_PORT"/ 2>&1 || true

echo "STEP done"
