#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1


if [ -z "$DISCORD_TOKEN" ]; then
   echo "Skipping Discord ingest test because the DISCORD_TOKEN env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
        --discord-channels 1099442333440802930,1099601456321003600 \
        --discord-token "$DISCORD_TOKEN" \
        --download-dir discord-ingest-download \
        --structured-output-dir discord-ingest-output \
        --reprocess

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

   cp discord-ingest-output/* test_unstructured_ingest/expected-structured-output/discord-ingest-channel/

elif ! diff -ru discord-ingest-output test_unstructured_ingest/expected-structured-output/discord-ingest-channel/; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo
   echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
   echo
   echo "  export OVERWRITE_FIXTURES=true"
   echo
   echo "and then rerun this script."
   echo
   echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
   echo "to update fixtures for CI."
   echo
   exit 1
fi
