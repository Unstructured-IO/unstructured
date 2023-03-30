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
    docker run -dt --rm --name "$CONTAINER_NAME" "$IMAGE_NAME"
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
until [ "$(docker inspect -f '{{.State.Status}}' $CONTAINER_NAME)" == "running" ]; do
    sleep 1
done

# Run the tests
docker cp test_unstructured_ingest $CONTAINER_NAME:/home
docker exec "$CONTAINER_NAME" /bin/bash -c "/home/test_unstructured_ingest/test-ingest-wikipedia.sh"

result=$?
exit $result
