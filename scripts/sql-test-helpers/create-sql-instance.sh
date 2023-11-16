#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
DATABASE_NAME=$1

# Create the SQL instance
if [[ "$DATABASE_NAME" != "sqlite" ]]; then
    docker compose version
    docker compose -f "$SCRIPT_DIR"/docker-compose-"$DATABASE_NAME".yaml up --wait
    docker compose -f "$SCRIPT_DIR"/docker-compose-"$DATABASE_NAME".yaml ps
fi

echo "$DATABASE_NAME instance is live."
