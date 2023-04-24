#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [ -z "$SLACK_TOKEN" ]; then
   echo "Skipping Slack ingest test because the SLACK_TOKEN env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
      --slack-channels C052BGT7718 \
      --slack-token "${SLACK_TOKEN}" \
      --download-dir slack-ingest-download \
      --structured-output-dir slack-ingest-output \
      --start-date 2023-04-01 \
      --end-date 2023-04-08T12:00:00-08:00

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

   cp slack-ingest-output/* test_unstructured_ingest/expected-structured-output/slack-ingest-channel/

elif ! diff -ru slack-ingest-output test_unstructured_ingest/expected-structured-output/slack-ingest-channel; then
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
