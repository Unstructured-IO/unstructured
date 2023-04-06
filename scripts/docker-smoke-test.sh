***REMOVED***!/bin/bash

***REMOVED*** Start the containerized repository and run ingest tests

***REMOVED*** shellcheck disable=SC2317  ***REMOVED*** Shellcheck complains that trap functions are unreachable...

set -eux -o pipefail

CONTAINER_NAME=unstructured-smoke-test
DOCKER_IMAGE="${DOCKER_IMAGE:-unstructured:dev}"

***REMOVED*** Change to the root of the repository
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
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

***REMOVED*** Regardless of test result, stop the container
trap stop_container EXIT

await_container

***REMOVED*** Run the tests
docker cp test_unstructured_ingest $CONTAINER_NAME:/home
docker exec "$CONTAINER_NAME" /bin/bash -c "/home/test_unstructured_ingest/test-ingest-wikipedia.sh"

result=$?
exit $result
