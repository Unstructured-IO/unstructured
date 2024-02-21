#!/usr/bin/env bash

# Structured .json output from PDF's or images may differ subtly (or not so subtly)
# based on the version of tesseract, its dependencies, and chip architecture.
#
# To update ingest-test expected outputs (structured .json files), this script:
#   * builds an ubuntu image that
#      * matches CI with respect to tesseract and OS deps
#      * installs python dependencies from the local requirements/ directory
#   * runs each test ingest script with OVERWRITE_FIXTURES=true
#      * so updates are written to test_unstructured_ingest/expected-structured-output/
#      * using local unstructured/ directory (i.e. from local git branch)
#
# It is recommended to run this script on x86_64 hardware.

set -eu -o pipefail

# Change to the root of the repository
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

ARCHITECTURE=$(uname -m)

if [ "$ARCHITECTURE" != "x86_64" ]; then
  echo "Warning: This script is designed to run on x86_64 hardware, but you're running on $ARCHITECTURE."
fi

./scripts/docker-build-ubuntu.sh

# Warn the user if they have an old image
IMAGE_NAME="unstructured-ubuntu:latest"
CREATION_TIMESTAMP=$(docker inspect --format='{{.Created}}' "$IMAGE_NAME")
CREATION_DATE=$(date -d "$CREATION_TIMESTAMP" +%s)
CURRENT_DATE=$(date +%s)
AGE_DAYS=$(((CURRENT_DATE - CREATION_DATE) / 86400))
if [ "$AGE_DAYS" -gt 6 ]; then
  echo "WARNING: The image \"$IMAGE_NAME\" is more than 7 days old ($AGE_DAYS days)."
  echo "You may want to 'docker rmi $IMAGE_NAME' and rerun this script if it is not current."
fi

docker run --rm -v "$SCRIPT_DIR"/../unstructured:/root/unstructured \
  -v "$SCRIPT_DIR"/../test_unstructured_ingest:/root/test_unstructured_ingest \
  ${DISCORD_TOKEN:+-e DISCORD_TOKEN="$DISCORD_TOKEN"} \
  ${SLACK_TOKEN:+-e SLACK_TOKEN="$SLACK_TOKEN"} \
  ${CONFLUENCE_USER_EMAIL:+-e CONFLUENCE_USER_EMAIL="$CONFLUENCE_USER_EMAIL"} \
  ${CONFLUENCE_API_TOKEN:+-e CONFLUENCE_API_TOKEN="$CONFLUENCE_API_TOKEN"} \
  ${GH_READ_ONLY_ACCESS_TOKEN:+-e GH_READ_ONLY_ACCESS_TOKEN="$GH_READ_ONLY_ACCESS_TOKEN"} \
  -w /root "$IMAGE_NAME" \
  bash -c "export OVERWRITE_FIXTURES=true && source ~/.bashrc && pyenv activate unstructured && tesseract --version &&
               ./test_unstructured_ingest/test-ingest-azure.sh &&
               ./test_unstructured_ingest/test-ingest-discord.sh &&
               ./test_unstructured_ingest/test-ingest-github.sh &&
               ./test_unstructured_ingest/test-ingest-biomed-api.sh &&
               ./test_unstructured_ingest/test-ingest-biomed-path.sh &&
               ./test_unstructured_ingest/test-ingest-s3.sh &&
               ./test_unstructured_ingest/test-ingest-slack.sh &&
               ./test_unstructured_ingest/test-ingest-pdf-fast-reprocess.sh &&
               ./test_unstructured_ingest/test-ingest-local-single-file-with-pdf-infer-table-structure.sh"
