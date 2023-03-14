***REMOVED***!/bin/bash

set -euo pipefail

DOCKER_BUILDKIT=1 docker buildx build --load --platform=linux/amd64 -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --progress plain \
  -t unstructured-dev:latest .
