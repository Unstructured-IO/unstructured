#!/usr/bin/env bash

DOCKER_IMAGE="${DOCKER_IMAGE:-unstructured:ci}"

DOCKER_BUILD_CMD=(docker buildx build --load -f ./CI/Dockerfile \
  --progress plain \
  -t "$DOCKER_IMAGE" .)

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"
