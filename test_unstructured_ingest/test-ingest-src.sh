#!/usr/bin/env bash

set -u -o pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
SKIPPED_FILES_LOG=$SCRIPT_DIR/skipped-files.txt
# If the file already exists, reset it
if [ -f "$SKIPPED_FILES_LOG" ]; then
  rm "$SKIPPED_FILES_LOG"
fi
touch "$SKIPPED_FILES_LOG"
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

all_tests=(
  's3.sh'
  's3-minio.sh'
  'azure.sh'
  'biomed-api.sh'
  'biomed-path.sh'
  # NOTE(yuming): The pdf-fast-reprocess test should be put after any tests that save downloaded files
  'pdf-fast-reprocess.sh'
  'salesforce.sh'
  'box.sh'
  'discord.sh'
  'dropbox.sh'
  'github.sh'
  'gitlab.sh'
  'google-drive.sh'
  'wikipedia.sh'
  'local.sh'
  'slack.sh'
  'against-api.sh'
  'gcs.sh'
  'onedrive.sh'
  'outlook.sh'
  'elasticsearch.sh'
  'confluence-diff.sh'
  'confluence-large.sh'
  'airtable-diff.sh'
  # NOTE(ryan): This test is disabled because it is triggering too many requests to the API
  # 'airtable-large.sh'
  'local-single-file.sh'
  'local-single-file-basic-chunking.sh'
  'local-single-file-with-encoding.sh'
  'local-single-file-with-pdf-infer-table-structure.sh'
  'notion.sh'
  'delta-table.sh'
  'jira.sh'
  'sharepoint.sh'
  'sharepoint-with-permissions.sh'
  'hubspot.sh'
  'local-embed.sh'
  'sftp.sh'
  'mongodb.sh'
  'opensearch.sh'
)

full_python_matrix_tests=(
  'sharepoint.sh'
  'local.sh'
  'local-single-file.sh'
  'local-single-file-with-encoding.sh'
  'local-single-file-with-pdf-infer-table-structure.sh'
  's3.sh'
  'google-drive.sh'
  'gcs.sh'
  'azure.sh'
)

CURRENT_TEST="none"

function print_last_run() {
  if [ "$CURRENT_TEST" != "none" ]; then
    echo "Last ran script: $CURRENT_TEST"
  fi
  echo "######## SKIPPED TESTS: ########"
  cat "$SKIPPED_FILES_LOG"
}

trap print_last_run EXIT

python_version=$(python --version 2>&1)

tests_to_ignore=(
  'notion.sh'
  'dropbox.sh'
)

for test in "${all_tests[@]}"; do
  CURRENT_TEST="$test"
  # IF: python_version is not 3.10 (wildcarded to match any subminor version) AND the current test is not in full_python_matrix_tests
  # Note: to test we expand the full_python_matrix_tests array to a string and then regex match the current test
  if [[ "$python_version" != "Python 3.10"* ]] && [[ ! "${full_python_matrix_tests[*]}" =~ $test ]]; then
    echo "--------- SKIPPING SCRIPT $test ---------"
    continue
  fi
  echo "--------- RUNNING SCRIPT $test ---------"
  echo "Running ./test_unstructured_ingest/$test"
  ./test_unstructured_ingest/src/"$test"
  rc=$?
  if [[ $rc -eq 8 ]]; then
    echo "$test (skipped due to missing env var)" | tee -a "$SKIPPED_FILES_LOG"
  elif [[ "${tests_to_ignore[*]}" =~ $test ]]; then
    echo "$test (skipped checking error code: $rc)" | tee -a "$SKIPPED_FILES_LOG"
    continue
  elif [[ $rc -ne 0 ]]; then
    exit $rc
  fi
  echo "--------- FINISHED SCRIPT $test ---------"
done

set +e

all_eval=(
  'text-extraction'
  'element-type'
)
for eval in "${all_eval[@]}"; do
  CURRENT_TEST="evaluation-metrics.sh $eval"
  echo "--------- RUNNING SCRIPT evaluation-metrics.sh $eval ---------"
  ./test_unstructured_ingest/evaluation-metrics.sh "$eval"
  echo "--------- FINISHED SCRIPT evaluation-metrics.sh $eval ---------"
done
