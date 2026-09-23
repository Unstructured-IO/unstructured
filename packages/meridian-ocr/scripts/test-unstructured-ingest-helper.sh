#!/usr/bin/env bash

# This is intended to be run from an unstructured checkout, not in this repo
# The goal here is to see what changes the current branch would introduce to unstructured
# fixtures

INGEST_COMMANDS=(
    test_unstructured_ingest/src/azure.sh
    test_unstructured_ingest/src/biomed-api.sh
    test_unstructured_ingest/src/biomed-path.sh
    test_unstructured_ingest/src/box.sh
    test_unstructured_ingest/src/dropbox.sh
    test_unstructured_ingest/src/gcs.sh
    test_unstructured_ingest/src/onedrive.sh
    test_unstructured_ingest/src/s3.sh
)

EXIT_STATUSES=()

# Run each command and capture its exit status
for INGEST_COMMAND in "${INGEST_COMMANDS[@]}"; do
  $INGEST_COMMAND
  EXIT_STATUSES+=($?)
done

# Check for failures
for STATUS in "${EXIT_STATUSES[@]}"; do
  if [[ $STATUS -ne 0 ]]; then
    echo "At least one ingest command failed! Scroll up to see which"
    exit 1
  fi
done

echo "No diff's resulted from any ingest commands"
