#!usr/bin/bash

SCRIPT_DIR=$(dirname "$(realpath "$0")")

function upload(){
    docker cp "$SCRIPT_DIR"/folder1/ sftp-test:/home/foo/upload/
}

# Create sftp server
docker compose version
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml up --wait
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml ps

echo "Cluster is live."
upload