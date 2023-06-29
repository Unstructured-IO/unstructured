#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/dropbox/ -type f -size +1 -not -name ".*" | wc -l)" -ne 4 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

if [ -z "$DROPBOX_APP_KEY" ] || [ -z "$DROPBOX_APP_SECRET" ] || [ -z "$DROPBOX_REFRESH_TOKEN" ]; then
   echo "Skipping Dropbox ingest test because one or more of these env vars is not set:"
   echo "DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN"
   exit 0
fi

# Get a new access token from Dropbox
DROPBOX_RESPONSE=$(curl https://api.dropbox.com/oauth2/token -d refresh_token=$DROPBOX_REFRESH_TOKEN -d grant_type=refresh_token -d client_id=$DROPBOX_APP_KEY -d client_secret=$DROPBOX_APP_SECRET)
DROPBOX_ACCESS_TOKEN=$(jq -r '.access_token' <<< $DROPBOX_RESPONSE)

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --remote-url "dropbox:// /" \
    --structured-output-dir dropbox-output \
    --dropbox-token  $DROPBOX_ACCESS_TOKEN \
    --recursive \
    --preserve-downloads \
    --reprocess 

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then
    EXPECTED_DIR=test_unstructured_ingest/expected-structured-output/dropbox
    [ -d "$EXPECTED_DIR" ] && rm -rf "$EXPECTED_DIR"
    cp -R dropbox-output $EXPECTED_DIR

elif ! diff -ru test_unstructured_ingest/expected-structured-output/dropbox dropbox-output ; then
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
    echo "to update fixtures for CI,"
    echo
    exit 1

fi
