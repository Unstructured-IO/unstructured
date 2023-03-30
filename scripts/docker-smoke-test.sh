#!/bin/bash

# Start the containerized repository and run ingest tests

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

set -eux -o pipefail

CONTAINER_NAME=unstructured-smoke-test
IMAGE_NAME="${IMAGE_NAME:-unstructured:latest}"

# Change to the root of the repository
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

start_container() {
    echo Starting container "$CONTAINER_NAME"
    docker run -d --rm --name "$CONTAINER_NAME" "$IMAGE_NAME"
}

stop_container() {
    echo Stopping container "$CONTAINER_NAME"
    docker stop "$CONTAINER_NAME"
}

start_container

# Regardless of test result, stop the container
trap stop_container EXIT

# Wait for the container to start
echo Waiting for container to start
docker wait "$CONTAINER_NAME"

# Run the tests
docker exec "$CONTAINER_NAME" /bin/bash -c "./test_unstructured_ingest/test-ingest-wikipedia.sh"



echo Running tests
PYTHONPATH=. pytest scripts/smoketest.py

result=$?
exit $result
