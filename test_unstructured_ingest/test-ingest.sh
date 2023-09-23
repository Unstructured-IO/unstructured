#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

scripts=(
'test-ingest-s3.sh'
'test-ingest-azure.sh'
'test-ingest-box.sh'
'test-ingest-discord.sh'
'test-ingest-dropbox.sh'
'test-ingest-github.sh'
'test-ingest-gitlab.sh'
'test-ingest-google-drive.sh'
'test-ingest-wikipedia.sh'
'test-ingest-biomed-api.sh'
'test-ingest-biomed-path.sh'
'test-ingest-local.sh'
'test-ingest-slack.sh'
'test-ingest-against-api.sh'
'test-ingest-gcs.sh'
'test-ingest-onedrive.sh'
'test-ingest-outlook.sh'
'test-ingest-elasticsearch.sh'
'test-ingest-confluence-diff.sh'
'test-ingest-confluence-large.sh'
'test-ingest-airtable-diff.sh'
# NOTE(ryan): This test is disabled because it is triggering too many requests to the API
# 'test-ingest-airtable-large.sh'
'test-ingest-local-single-file.sh'
'test-ingest-local-single-file-with-encoding.sh'
'test-ingest-local-single-file-with-pdf-infer-table-structure.sh'
'test-ingest-notion.sh'
'test-ingest-delta-table.sh'
'test-ingest-salesforce.sh'
'test-ingest-jira.sh'
## NOTE(yuming): The following test should be put after any tests with --preserve-downloads option
'test-ingest-pdf-fast-reprocess.sh'
'test-ingest-sharepoint.sh'
)

PIDS=""
FAIL=0

for script in "${scripts[@]}"; do
  CURRENT_SCRIPT="$script"
  if [[ "$CURRENT_SCRIPT" == "test-ingest-notion.sh" ]]; then
    echo "--------- RUNNING SCRIPT $script --- IGNORING FAILURES"
    set +e
    echo "Running ./test_unstructured_ingest/$script"
    ./test_unstructured_ingest/"$script"
    set -e
    echo "--------- FINISHED SCRIPT $script ---------"
  else
    echo "--------- RUNNING SCRIPT $script ---------"
    echo "Running ./test_unstructured_ingest/$script"
    ./test_unstructured_ingest/"$script" & PIDS="$PIDS $!"
    echo "--------- FINISHED SCRIPT $script ---------"
  fi
done

for job in "$PIDS"
do
    wait "$job" || let "FAIL+=1"
    echo "$job" "$FAIL"
done

if [ "$FAIL" == "0" ];
then
    exit 0
else
    exit 1
fi