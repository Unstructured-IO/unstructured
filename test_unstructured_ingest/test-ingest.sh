#!/usr/bin/env bash

set -eux -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

./test_unstructured_ingest/test-ingest-s3.sh
./test_unstructured_ingest/test-ingest-azure.sh
./test_unstructured_ingest/test-ingest-github.sh
./test_unstructured_ingest/test-ingest-gitlab.sh
./test_unstructured_ingest/test-ingest-wikipedia.sh
./test_unstructured_ingest/test-ingest-biomed-api.sh
./test_unstructured_ingest/test-ingest-biomed-path.sh
./test_unstructured_ingest/test-ingest-local.sh
./test_unstructured_ingest/test-ingest-slack.sh
./test_unstructured_ingest/test-ingest-against-api.sh
