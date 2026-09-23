#!/usr/bin/env bash

# Start the containerized repository and run ingest tests

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...
# shellcheck disable=SC2329  # Functions are invoked indirectly

set -eux -o pipefail

CONTAINER_NAME=meridian_partition-smoke-test
DOCKER_IMAGE="${DOCKER_IMAGE:-meridian_partition:dev}"

# Change to the root of the meridian-partition package
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
CONTAINER_PACKAGE_DIR=/app/packages/meridian-partition
docker cp test_unstructured_ingest $CONTAINER_NAME:$CONTAINER_PACKAGE_DIR
docker exec -u root "$CONTAINER_NAME" /bin/bash -c "chown -R notebook-user:notebook-user $CONTAINER_PACKAGE_DIR/test_unstructured_ingest"
docker exec "$CONTAINER_NAME" /bin/bash -c "$CONTAINER_PACKAGE_DIR/test_unstructured_ingest/src/local.sh"

result=$?
exit $result
