#!/bin/bash

set -euo pipefail
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-linux/amd64}"
if [[ $DOCKER_BUILD_PLATFORM == "linux/amd64" ]]; then
    DOCKER_ARCH_TAG="amd"
elif [[ $DOCKER_BUILD_PLATFORM == "linux/arm64" ]]; then
    DOCKER_ARCH_TAG="arm"
else
    echo "Unsupported platform: $DOCKER_BUILD_PLATFORM"
    exit 1
fi
DOCKER_BUILD_REPOSITORY="${DOCKER_BUILD_REPOSITORY:-quay.io/unstructured-io/unstructured}"
PIPELINE_PACKAGE="${PIPELINE_PACKAGE:-general}"
PIP_VERSION="${PIP_VERSION:-22.2.1}"

DOCKER_BUILDKIT=1 docker buildx build --load --platform="$DOCKER_BUILD_PLATFORM" -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --progress plain \
  --cache-from "$DOCKER_BUILD_REPOSITORY":latest \
  -t unstructured:dev .
