# loki-boot

Publishes one boot event to Grafana Loki containing the service name, IPv4
address and nanosecond timestamp. Set `LOKI_URL`, `LOKI_USER`, `LOKI_TOKEN`
and `SERVICE_NAME` (see [.env.template](.env.template)).

## IP discovery

1. Set `PRIVATE_IP` to explicitly supply a known task/host IPv4 address. This
   bypasses discovery; an invalid override fails instead of silently falling back.
2. In ECS, the publisher uses `ECS_CONTAINER_METADATA_URI_V4`, or the v3
   `ECS_CONTAINER_METADATA_URI` when v4 is absent. These are supplied by ECS;
   do not hard-code another task's metadata URI. It looks for an `awsvpc`
   address in container metadata, then in `/task` metadata if needed.
3. Outside ECS, it selects the first usable IPv4 address from `hostname -I`.

Addresses must be valid dotted-decimal IPv4, excluding unspecified, loopback,
link-local, multicast/reserved and ambiguous leading-zero addresses. The code
does not restrict addresses to RFC 1918 ranges, since VPCs can use other ranges.

ECS metadata discovery retries five times, with two seconds between attempts.
Each attempt tries both endpoints if needed; each request has a two-second
connection timeout and five-second total timeout. Metadata discovery therefore
has a request/sleep budget of at most 58 seconds (plus processing overhead).
Metadata requests bypass HTTP proxies. Both transport failures and successful
responses with malformed JSON or missing/invalid addresses are retried.

If discovery still fails, the publisher exits with code 1, writes a diagnostic
to stderr, and does **not** send a boot event with an incorrect or empty IP.
It never falls back to `hostname -I` when an ECS metadata URI is supplied, or
when `AWS_EXECUTION_ENV` identifies ECS. Check metadata endpoint access and
`awsvpc` networking, or set `PRIVATE_IP` to the known task ENI address. IPv6-only
tasks require separate IPv6 support; they cannot supply this event's IPv4 field.

This is a one-shot publisher: exit code 0 after a successful Loki push is normal.
In ECS, configure it as a non-essential sidecar so its completion does not stop
the application. Failed Loki pushes retain curl's nonzero exit code.

## Checks

With Bash, jq and Python 3 installed:

```sh
bash -n loki-boot/debian/loki-boot.sh
python3 -m unittest discover -s tests -v
```

Tests run the actual script and jq parser with mocked metadata/hostname/Loki
transports; they do not access AWS or send events to Loki.
