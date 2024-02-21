#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=clarifai-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
writer_processes=$(((max_processes - 1) > 1 ? (max_processes - 1) : 2))

if [ -z "$CLARIFAI_PAT" ]; then
    echo "Skipping Clarifai ingest test because CLARIFAI_PAT env var is not set."
    exit 0

fi

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))
# Set the variables with default values 
USER_ID="clarifai"
APP_ID="test-app-unstructured-$RANDOM_SUFFIX"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
    # Get response code to check if app really exists
    response_code=$(curl \
    -s -o /dev/null \
    -w "%{http_code}" \
    --request GET "https://api.clarifai.com/v2/users/$USER_ID/apps/$APP_ID" \
    --header "Authorization: Key $CLARIFAI_PAT" )

    # Cleanup (delete) index if it exists
    if [ "$response_code" == "200" ]; then
        echo ""
        echo "deleting clarifai app $APP_ID"
        curl --request DELETE "https://api.clarifai.com/v2/users/$USER_ID/apps/$APP_ID" \
        -H "Authorization: Key $CLARIFAI_PAT"
    
    else
        echo "There was an error during deletion of clarifai app $APP_ID, with response code: $response_code. App might not exists in your account."
    fi 
    # Local file cleanup
    cleanup_dir "$WORK_DIR"
    cleanup_dir "$OUTPUT_DIR"
    }

trap cleanup EXIT

echo "Creating Clarifai app $APP_ID"
response_code=$(curl \
    -s -o /dev/null \
    -w "%{http_code}" \
    --location --request POST "https://api.clarifai.com/v2/users/$USER_ID/apps/" \
    --header "Content-Type: application/json" \
    --header "Authorization: Key $CLARIFAI_PAT" \
    --data-raw "{\"apps\": [{\"id\": \"$APP_ID\"}]}"
)
if [ "$response_code" -lt 400 ]; then 
    echo "App created successfully: $APP_ID"
else
    echo "Failed to create app $APP_ID: $response_code"
    exit 1
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --chunk-elements \
  --num-processes "$max_processes" \
  --work-dir "$WORK_DIR" \
  --verbose \
  clarifai \
  --app-id "$APP_ID" \
  --user-id "$USER_ID" \
  --api-key "$CLARIFAI_PAT"\
  --batch-size 100 \
  --num-processes "$writer_processes" 

no_of_inputs=0
sleep_time=10

while [ "$no_of_inputs" -eq 0 ]; do
    echo "checking for no of inputs in clarifai app"
    sleep $sleep_time

    resp=$(curl \
     -s GET "https://api.clarifai.com/v2/users/$USER_ID/apps/$APP_ID/inputs/status" \
     -H "Authorization: Key $CLARIFAI_PAT")

    no_of_inputs=$(echo "$resp" |jq -r '.counts.processed' | sed 's/\x1b\[[0-9;]*m//g')
    echo "Processed count: $no_of_inputs"
done

EXPECTED=8729

if [ "$no_of_inputs" -lt 1 ] || [ "$no_of_inputs" -ne "$EXPECTED" ]; then  
    echo "Number of inputs in the clarifai app $APP_ID is less than expected. Test failed."
    exit 1

fi