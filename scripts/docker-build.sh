#!/usr/bin/env bash

set -euo pipefail
DOCKER_REPOSITORY="${DOCKER_REPOSITORY:-quay.io/unstructured-io/unstructured}"
PIP_VERSION="${PIP_VERSION:-23.1.2}"
DOCKER_IMAGE="${DOCKER_IMAGE:-unstructured:dev}"

DOCKER_BUILD_CMD=(docker buildx build --load -f Dockerfile
  --build-arg PIP_VERSION="$PIP_VERSION"
  --build-arg BUILDKIT_INLINE_CACHE=1
  --progress plain
  --cache-from "$DOCKER_REPOSITORY":latest
  -t "$DOCKER_IMAGE" .)

# only build for specific platform if DOCKER_BUILD_PLATFORM is set
if [ -n "${DOCKER_BUILD_PLATFORM:-}" ]; then
  DOCKER_BUILD_CMD+=("--platform=$DOCKER_BUILD_PLATFORM")
fi

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"
