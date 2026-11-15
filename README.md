# loki-boot

One-shot boot event → Grafana Loki
ECS sidecar · non-essential
Runtime: Bash · curl · jq

## ECS task definition

Required:
- Environment: `LOKI_URL`, `SERVICE_NAME`
- Secrets: `LOKI_USER`, `LOKI_TOKEN`

```json
{
  "environment": [
    { "name": "LOKI_URL", "value": "https://loki.example" },
    { "name": "SERVICE_NAME", "value": "event-publisher" },
    { "name": "SERVICE_PORT", "value": "8080" },
    { "name": "SERVICE_PROTOCOL", "value": "https" },
    { "name": "SERVICE_URI", "value": "/api" },
    { "name": "ECS_NETWORK_MODE", "value": "auto" }
  ],
  "secrets": [
    { "name": "LOKI_USER", "valueFrom": "arn:aws:secretsmanager:..." },
    { "name": "LOKI_TOKEN", "valueFrom": "arn:aws:secretsmanager:..." }
  ]
}
```

Optional:
- `SERVICE_PORT`: 1–65535
- `SERVICE_PROTOCOL`: `http` / `https`
- `SERVICE_URI`: path, e.g. `/api`
- `ECS_NETWORK_MODE`: `auto` (default), `awsvpc`, `host`
- `PRIVATE_IP`: explicit override

ECS metadata URI: injected by ECS · Host networking: EC2 IMDSv2
