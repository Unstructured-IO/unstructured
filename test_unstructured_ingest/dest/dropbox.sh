#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=dropbox-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_DROPBOX="/test-output/$(uuidgen)"
CI=${CI:-"false"}

if [ -z "$DROPBOX_APP_KEY" ] || [ -z "$DROPBOX_APP_SECRET" ] || [ -z "$DROPBOX_REFRESH_TOKEN" ]; then
  echo "Skipping Dropbox ingest test because one or more of these env vars is not set:"
  echo "DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN"
  exit 8
fi

# Get a new access token from Dropbox
DROPBOX_RESPONSE=$(curl -s https://api.dropbox.com/oauth2/token -d refresh_token="$DROPBOX_REFRESH_TOKEN" -d grant_type=refresh_token -d client_id="$DROPBOX_APP_KEY" -d client_secret="$DROPBOX_APP_SECRET")
DROPBOX_ACCESS_TOKEN=$(jq -r '.access_token' <<<"$DROPBOX_RESPONSE")

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  echo "deleting test folder $DESTINATION_DROPBOX"
  curl -X POST https://api.dropboxapi.com/2/files/delete_v2 \
    --header "Content-Type: application/json" \
    --header "Authorization: Bearer $DROPBOX_ACCESS_TOKEN" \
    --data "{\"path\":\"$DESTINATION_DROPBOX\"}" | jq
}
trap cleanup EXIT

# Create new folder for test
echo "creating temp directory in dropbox for testing: $DESTINATION_DROPBOX"
response=$(curl -X POST -s -w "\n%{http_code}" https://api.dropboxapi.com/2/files/create_folder_v2 \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $DROPBOX_ACCESS_TOKEN" \
  --data "{\"autorename\":false,\"path\":\"$DESTINATION_DROPBOX\"}")
http_code=$(tail -n1 <<<"$response") # get the last line
content=$(sed '$ d' <<<"$response")  # get all but the last line which contains the status code

if [ "$http_code" -ge 300 ]; then
  echo "Failed to create temp dir in dropbox: [$http_code] $content"
  exit 1
else
  echo "$http_code:"
  jq <<<"$content"
fi

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  dropbox \
  --token "$DROPBOX_ACCESS_TOKEN" \
  --remote-url "dropbox://$DESTINATION_DROPBOX"

# Simply check the number of files uploaded
expected_num_files=1
num_files_in_dropbox=$(curl -X POST https://api.dropboxapi.com/2/files/list_folder \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $DROPBOX_ACCESS_TOKEN" \
  --data "{\"path\":\"$DESTINATION_DROPBOX/\"}" | jq '.entries | length')
if [ "$num_files_in_dropbox" -ne "$expected_num_files" ]; then
  echo "Expected $expected_num_files files to be uploaded to dropbox, but found $num_files_in_dropbox files."
  exit 1
fi
