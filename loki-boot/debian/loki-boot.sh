#!/usr/bin/env bash
set -euo pipefail

valid_ipv4() {
  local octet
  local -a octets
  [[ "$1" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || return 1
  IFS=. read -r -a octets <<< "$1"
  for octet in "${octets[@]}"; do
    # Reject ambiguous leading-zero notation as well as out-of-range octets.
    [[ "$octet" == 0 || "$octet" != 0* ]] || return 1
    (( 10#$octet <= 255 )) || return 1
  done
  # Ignore unspecified, loopback, link-local, multicast and reserved addresses.
  (( octets[0] > 0 && octets[0] != 127 && octets[0] < 224 )) || return 1
  [[ "${octets[0]}.${octets[1]}" != 169.254 ]]
}

discover_ip() {
  local metadata_uri metadata candidates candidate endpoint attempt addresses

  if [[ -n "${PRIVATE_IP:-}" ]]; then
    if valid_ipv4 "$PRIVATE_IP"; then
      printf '%s\n' "$PRIVATE_IP"
      return 0
    fi
    echo "PRIVATE_IP must be a usable IPv4 address" >&2
    return 1
  fi

  metadata_uri=${ECS_CONTAINER_METADATA_URI_V4:-${ECS_CONTAINER_METADATA_URI:-}}
  if [[ -n "$metadata_uri" ]]; then
    metadata_uri=${metadata_uri%/}
    # Retry the whole fetch/parse operation: HTTP success does not mean the
    # network address is ready. Task metadata can supply a missing container IP.
    for attempt in {1..5}; do
      for endpoint in "$metadata_uri" "$metadata_uri/task"; do
        if metadata=$(curl -fsS --noproxy '*' --connect-timeout 2 --max-time 5 "$endpoint"); then
          if candidates=$(jq -er '
            [.Networks[]?, .Containers[]?.Networks[]?][]
            | select(.NetworkMode == "awsvpc")
            | .IPv4Addresses[]? | strings
          ' <<< "$metadata" 2>/dev/null); then
            while IFS= read -r candidate; do
              if valid_ipv4 "$candidate"; then
                printf '%s\n' "$candidate"
                return 0
              fi
            done <<< "$candidates"
          fi
        fi
      done
      echo "ECS metadata attempt $attempt/5: no usable awsvpc IPv4 address (unavailable, invalid JSON, or missing address)" >&2
      if (( attempt < 5 )); then sleep 2; fi
    done
    echo "Could not determine the ECS task awsvpc IPv4 address; check ECS metadata access/network mode or set PRIVATE_IP explicitly" >&2
    return 1
  fi

  if [[ "${AWS_EXECUTION_ENV:-}" == AWS_ECS* ]]; then
    echo "ECS metadata URI is missing; enable ECS container metadata or set PRIVATE_IP explicitly" >&2
    return 1
  fi

  # Only use host interfaces outside ECS: they may be unrelated to the task ENI.
  if addresses=$(hostname -I); then
    for candidate in $addresses; do
      if valid_ipv4 "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi
  echo "Could not determine a usable host IPv4 address; set PRIVATE_IP explicitly" >&2
  return 1
}

IP=$(discover_ip)
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
