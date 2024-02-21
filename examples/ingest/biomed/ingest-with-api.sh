#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in biomed-ingest-output-api/

# Biomedical documents can be extracted in one of two ways, in this script is the API approach.

# Through the OA Web Service API and the parameters provided here: https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
# The format parameter is the only unsupported parameter. Format will always be PDF as .tar.gz files aren't

# For example, to download documents from 2019-01-02 00:00:00 to 2019-01-02+00:03:10"
# the parameters "from" and "until" are needed

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  biomed \
  --api-from "2019-01-02" \
  --api-until "2019-01-02+00:03:10" \
  --output-dir biomed-ingest-output-api \
  --num-processes 2 \
  --verbose \
  --preserve-downloads

# Alternatively, you can call it using:
# unstructured-ingest --biomed-api ...
