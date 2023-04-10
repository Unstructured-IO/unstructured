#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [ -z "$SLACK_CHANNEL" ] || [ -z "$SLACK_TOKEN" ]; then
   echo "Skipping Slack ingest test because SLACK_CHANNEL and SLACK_TOKEN env vars are not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
        --slack-channel "${SLACK_CHANNEL}" \
        --slack-token "${SLACK_TOKEN}" \
        --download-dir slack-ingest-download \
        --structured-output-dir slack-ingest-output \
        --start-date 2023-04-01 \
        --end-date 2023-04-08T12:00:00-08:00

if ! diff -ru slack-ingest-output test_unstructured_ingest/expected-structured-output/slack-ingest-channel; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "slack-ingest-output/ to test_unstructured_ingest/expected-structured-output/slack-ingest-channel/ after running"
   echo 
   echo "PYTHONPATH=. ./unstructured/ingest/main.py --slack-channel ${SLACK_CHANNEL} --slack-token ${SLACK_TOKEN} --download-dir slack-ingest-download --structured-output-dir slack-ingest-output --start-date 2023-04-01 --end-date 2023-04-08T12:00:00-08:00 --verbose"
   echo
   exit 1
fi
