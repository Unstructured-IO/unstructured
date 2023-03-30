#!/bin/bash

# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

CONTAINER_NAME=unstructured-smoketest
IMAGE_NAME="${IMAGE_NAME:-unstructured:latest}"

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
