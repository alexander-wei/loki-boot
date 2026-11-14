# loki-boot

Send a startup event to Grafana Loki using the Debian systemd service or a
one-shot Docker container.

## Docker

Build from the repository root:

```sh
docker build -t loki-boot:local .
```

Provide these environment variables at runtime; do not bake credentials into
the image:

| Variable | Meaning |
| --- | --- |
| `LOKI_URL` | Loki base URL, e.g. `https://loki.example.com`, without `/loki/api/v1/push` |
| `LOKI_USER` | Loki basic-auth username |
| `LOKI_TOKEN` | Loki basic-auth token |
| `SERVICE_NAME` | Value for the `service_name` stream label |

With those variables exported in your shell:

```sh
docker run --rm \
  -e LOKI_URL -e LOKI_USER -e LOKI_TOKEN -e SERVICE_NAME \
  loki-boot:local
```

The container runs as an unprivileged user, sends one event, and exits. It does
not need systemd inside Docker. Each invocation reports container startup, not
host boot; the `private_ip` field is the container IP on its Docker network.
Do not use an always-restart policy: successful exits would repeatedly send
events. Arrange host-boot invocation separately if host-boot reporting is needed.
