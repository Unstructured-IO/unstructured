#!/usr/bin/env bash

set -eux -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

./test_unstructured_ingest/test-ingest-s3.sh
./test_unstructured_ingest/test-ingest-github.sh
./test_unstructured_ingest/test-ingest-wikipedia.sh
