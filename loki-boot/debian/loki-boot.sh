#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${ECS_CONTAINER_METADATA_URI_V4:-}" ]]; then
  # In awsvpc mode, ECS metadata exposes the task ENI's private IPv4 address.
  # hostname -I can return a different interface address inside the container.
  IP=$(curl -fsS "$ECS_CONTAINER_METADATA_URI_V4" |
    jq -er '[.Networks[]? | select(.NetworkMode == "awsvpc") | .IPv4Addresses[]?][0] // empty')
  if [[ -z "$IP" ]]; then
    echo "Could not determine the ECS task awsvpc private IP from container metadata" >&2
    exit 1
  fi
else
  IP=$(hostname -I | awk '{print $1}')
fi
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
