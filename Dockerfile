# Dockerfile
# Minimal image to run the loki-boot service script

FROM debian:slim

# Install required tools: bash, curl, jq, coreutils
RUN apt-get update && \
    apt-get install -y bash curl jq coreutils && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /usr/local/bin

# Copy necessary files from the cloned repository
# Assuming the scripts are located under loki-boot/loki-boot/debian/
COPY loki-boot/loki-boot/debian/loki-boot.sh ./loki-boot.sh
COPY loki-boot/loki-boot/debian/loki-boot.sh.env ./ # Placeholder for environment file if needed

# Set execution permissions
RUN chmod +x ./loki-boot.sh

# Define the entry point to run the script
ENTRYPOINT ["./loki-boot.sh"]

# Environment variables should be set when running the container
# Example:
# ENV LOKI_URL="http://loki:3100/loki/api/v1/push"
# ENV LOKI_USER="user"
# ENV LOKI_TOKEN="token"
# ENV SERVICE_NAME="my-service"