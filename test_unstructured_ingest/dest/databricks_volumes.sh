#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=databricks-volumes-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

if [ -z "$DATABRICKS_TOKEN" ] && [ -z "$DATABRICKS_HOST" ];  then
   echo "Skipping Databricks volumes destination ingest test because the DATABRICKS_TOKEN and DATABRICKS_HOST env vars are not set."
   exit 0
fi

catalog_name=utic-dev-tech-fixtures
schema_name=default
volume_type=MANAGED
volume_name=ingest-test-$(date +%s)
volume_path=default/$volume_name

full_path="/Volumes/$catalog_name/$volume_path"
volume_path_w_periods=$(echo "$volume_path" | tr '/' '.')
full_name="$catalog_name.$volume_path_w_periods"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  echo "deleting databricks volume storage directory $full_name"
  curl -X DELETE -s \
  "$DATABRICKS_HOST"/api/2.1/unity-catalog/volumes/"$full_name" \
  --header "Authorization: Bearer $DATABRICKS_TOKEN" | jq

}
trap cleanup EXIT

# Create directory to use for testing
create_data="{\"catalog_name\": \"$catalog_name\", \"schema_name\": \"$schema_name\", \"name\": \"$volume_name\", \"volume_type\": \"$volume_type\"}"
echo "Creating new volume based on: $create_data"
response=$(curl -X POST -s -w "\n%{http_code}" \
  "$DATABRICKS_HOST"/api/2.1/unity-catalog/volumes \
  --header "Authorization: Bearer $DATABRICKS_TOKEN" \
  --data "$create_data");
http_code=$(tail -n1 <<< "$response")  # get the last line
content=$(sed '$ d' <<< "$response")   # get all but the last line which contains the status code

if [ "$http_code" -ge 300 ]; then
  echo "Failed to create temp dir in dropbox: [$http_code] $content"
  exit 1
else
  echo "$http_code:"
  jq <<< "$content"
fi


PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --num-processes "$max_processes" \
    --output-dir "$OUTPUT_DIR" \
    --strategy fast \
    --verbose \
    --reprocess \
    --input-path example-docs/fake-memo.pdf \
    --work-dir "$WORK_DIR" \
    databricks-volumes \
    --token "$DATABRICKS_TOKEN" \
    --host "$DATABRICKS_HOST" \
    --remote-url "$full_path" \
    --overwrite

# Simply check that the expected file exists
expected_file_path=$full_path/example-docs/fake-memo.pdf.json
echo "Checking that $expected_file_path exists"
response=$(curl --head -s -w "\n%{http_code}" \
  "$DATABRICKS_HOST"/api/2.0/fs/files"$expected_file_path" \
  --header "Authorization: Bearer $DATABRICKS_TOKEN");
http_code=$(tail -n1 <<< "$response")  # get the last line
content=$(sed '$ d' <<< "$response")   # get all but the last line which contains the status code
if [ "$http_code" -ge 300 ]; then
  echo "Failed to validate that file uploaded to $expected_file_path: [$http_code] $content"
  exit 1
else
  echo "File was found as expected!"
fi
