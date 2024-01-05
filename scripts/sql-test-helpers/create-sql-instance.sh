#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
DATABASE_NAME=$1
DATABASE_FILE_PATH=$2

# Create the SQL instance
if [[ "$DATABASE_NAME" != "sqlite" ]]; then
  docker compose version
  docker compose -f "$SCRIPT_DIR"/docker-compose-"$DATABASE_NAME".yaml up --wait
  docker compose -f "$SCRIPT_DIR"/docker-compose-"$DATABASE_NAME".yaml ps
else
  touch "$DATABASE_FILE_PATH"

  python "$SCRIPT_DIR"/create-sqlite-schema.py "$DATABASE_FILE_PATH"
fi

echo "$DATABASE_NAME instance is live."
