#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Create the Elasticsearch cluster
docker compose version
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml up --wait
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml ps


echo "Cluster is live."
"$SCRIPT_DIR"/create_and_fill_es.py
