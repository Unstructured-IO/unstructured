#!/usr/bin/env bash

# Start the containerized repository and run ingest tests

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

set -eux -o pipefail

CONTAINER_NAME=unstructured-smoke-test
DOCKER_IMAGE="${DOCKER_IMAGE:-unstructured:dev}"

# Change to the root of the repository
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

start_container() {
  echo Starting container "$CONTAINER_NAME"
  docker run -dt --rm --name "$CONTAINER_NAME" "$DOCKER_IMAGE"
}

await_container() {
  echo Waiting for container to start
  until [ "$(docker inspect -f '{{.State.Status}}' $CONTAINER_NAME)" == "running" ]; do
    sleep 1
  done
}

stop_container() {
  echo Stopping container "$CONTAINER_NAME"
  docker stop "$CONTAINER_NAME"
}

start_container

# Regardless of test result, stop the container
trap stop_container EXIT

await_container

# Run the tests
docker cp test_unstructured_ingest $CONTAINER_NAME:/home/notebook-user
docker exec -u root "$CONTAINER_NAME" /bin/bash -c "chown -R 1000:1000 /home/notebook-user/test_unstructured_ingest"
docker exec "$CONTAINER_NAME" /bin/bash -c "/home/notebook-user/test_unstructured_ingest/src/wikipedia.sh"

result=$?
exit $result
