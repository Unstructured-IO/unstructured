#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

all_tests=(
'test-ingest-s3.sh'
'test-ingest-s3-minio.sh'
'test-ingest-azure.sh'
'test-ingest-biomed-api.sh'
'test-ingest-biomed-path.sh'
# NOTE(yuming): The pdf-fast-reprocess test should be put after any tests that save downloaded files
'test-ingest-pdf-fast-reprocess.sh'
'test-ingest-salesforce.sh'
'test-ingest-box.sh'
'test-ingest-discord.sh'
'test-ingest-dropbox.sh'
'test-ingest-github.sh'
'test-ingest-gitlab.sh'
'test-ingest-google-drive.sh'
'test-ingest-wikipedia.sh'
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
'test-ingest-jira.sh'
'test-ingest-sharepoint.sh'
'test-ingest-embed.sh'
)

full_python_matrix_tests=(
  'test-ingest-sharepoint.sh'
  'test-ingest-local.sh'
  'test-ingest-local-single-file.sh'
  'test-ingest-local-single-file-with-encoding.sh'
  'test-ingest-local-single-file-with-pdf-infer-table-structure.sh'
  'test-ingest-s3.sh'
  'test-ingest-google-drive.sh'
  'test-ingest-gcs.sh'
)

CURRENT_TEST="none"

function print_last_run() {
  if [ "$CURRENT_TEST" != "none" ]; then
    echo "Last ran script: $CURRENT_TEST"
  fi
}

trap print_last_run EXIT

python_version=$(python --version 2>&1)

for test in "${all_tests[@]}"; do
  CURRENT_TEST="$test"
  # IF: python_version is not 3.10 (wildcarded to match any subminor version) AND the current test is not in full_python_matrix_tests
  # Note: to test we expand the full_python_matrix_tests array to a string and then regex match the current test
  if [[ "$python_version" != "Python 3.10"* ]] && [[ ! "${full_python_matrix_tests[*]}" =~ $test ]] ; then
    echo "--------- SKIPPING SCRIPT $test ---------"
    continue
  fi
  if [[ "$test" == "test-ingest-notion.sh" ]]; then
    echo "--------- RUNNING SCRIPT $test --- IGNORING FAILURES"
    set +e
    echo "Running ./test_unstructured_ingest/$test"
    ./test_unstructured_ingest/"$test"
    set -e
    echo "--------- FINISHED SCRIPT $test ---------"
  else
    echo "--------- RUNNING SCRIPT $test ---------"
    echo "Running ./test_unstructured_ingest/$test"
    ./test_unstructured_ingest/"$test"
    echo "--------- FINISHED SCRIPT $test ---------"
  fi
done
