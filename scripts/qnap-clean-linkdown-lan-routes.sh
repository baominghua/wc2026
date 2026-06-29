#!/bin/sh
set -u

LAN_CIDR="${1:-192.168.100.0/24}"
KEEP_DEV="${2:-eth1}"
LOG_PATH="${3:-/share/CACHEDEV1_DATA/Web/wc2026/logs/qnap-route-guard.log}"

PATH="/sbin:/bin:/usr/sbin:/usr/bin:$PATH"

mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true

changed=0
before="$(ip route show "$LAN_CIDR" 2>/dev/null || true)"

for dev in $(printf "%s\n" "$before" | awk '$3 ~ /^qvs[0-9]+$/ && /linkdown/ { print $3 }' | sort -u); do
  [ "$dev" = "$KEEP_DEV" ] && continue
  if ip route del "$LAN_CIDR" dev "$dev" 2>/dev/null; then
    if [ "$changed" -eq 0 ]; then
      {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] cleaning stale LAN routes"
        echo "before:"
        printf "%s\n" "$before"
      } >> "$LOG_PATH"
    fi
    echo "deleted: $LAN_CIDR dev $dev" >> "$LOG_PATH"
    changed=1
  fi
done

if [ "$changed" -eq 1 ]; then
  ip route flush cache 2>/dev/null || true
  {
    echo "after:"
    ip route show "$LAN_CIDR" 2>/dev/null || true
    echo "route to LAN client:"
    ip route get 192.168.100.26 2>/dev/null || true
    echo
  } >> "$LOG_PATH"
fi
