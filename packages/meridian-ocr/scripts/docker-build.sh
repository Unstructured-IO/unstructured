#!/usr/bin/env bash

set -euo pipefail
DOCKER_IMAGE="${DOCKER_IMAGE:-unstructured-inference:dev}"

DOCKER_BUILD_CMD=(docker buildx build --load -f Dockerfile \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --progress plain \
  -t "$DOCKER_IMAGE" .)

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"
