#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Create the Postgres instance
docker compose version
docker compose -f "$SCRIPT_DIR"/docker-compose.yml up --wait
docker compose -f "$SCRIPT_DIR"/docker-compose.yml ps

echo "Postgres instance is live."