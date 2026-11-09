#!/usr/bin/env bash
set -euo pipefail

IP=$(hostname -I | awk '{print $1}')
TS=$(date +%s%N)

DATA=$(jq -nc \
  --arg service "$SERVICE_NAME" \
  --arg ip "$IP" \
  --arg ts "$TS" \
  '{streams:[{stream:{service_name:$service},values:[[$ts, ({private_ip:$ip,timestamp:$ts} | tojson)]]}]}')

curl -sS --fail-with-body --retry 5 --retry-delay 3 \
  -u "$LOKI_USER:$LOKI_TOKEN" \
  -H "Content-Type: application/json" \
  --data-raw "$DATA" \
  "$LOKI_URL/loki/api/v1/push"
