#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(dirname "$(realpath "$0")")")
# Create the Elasticsearch cluster
docker compose version
docker compose -f "$SCRIPT_DIR"/common/docker-compose.yaml up --wait
docker compose -f "$SCRIPT_DIR"/common/docker-compose.yaml ps


echo "Cluster is live."
"$SCRIPT_DIR"/destination_connector/create_index.py
