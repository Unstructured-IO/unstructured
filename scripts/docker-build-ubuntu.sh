#!/usr/bin/env bash

# Mainly useful for building an image from which to update test-ingest fixtures

set -eu -o pipefail

# Change to the root of the repository
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

docker build -t unstructured-ubuntu:latest --progress plain -f docker/ubuntu-22/Dockerfile .
