FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl jq coreutils \
    && rm -rf /var/lib/apt/lists/*

COPY --chmod=755 loki-boot/debian/loki-boot.sh /usr/local/bin/loki-boot

USER 65534:65534
ENTRYPOINT ["/usr/local/bin/loki-boot"]
