#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
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
'local-single-file-with-encoding.sh'
'local-single-file-with-pdf-infer-table-structure.sh'
'notion.sh'
'delta-table.sh'
'jira.sh'
'sharepoint.sh'
'embed.sh'
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
)

CURRENT_TEST="none"

function print_last_run() {
  if [ "$CURRENT_TEST" != "none" ]; then
    echo "Last ran script: $CURRENT_TEST"
  fi
}

trap print_last_run EXIT

python_version=$(python --version 2>&1)

tests_to_ignore=(
  'notion.sh'
  'dropbox.sh'
  'sharepoint.sh'
)

for test in "${all_tests[@]}"; do
  CURRENT_TEST="$test"
  # IF: python_version is not 3.10 (wildcarded to match any subminor version) AND the current test is not in full_python_matrix_tests
  # Note: to test we expand the full_python_matrix_tests array to a string and then regex match the current test
  if [[ "$python_version" != "Python 3.10"* ]] && [[ ! "${full_python_matrix_tests[*]}" =~ $test ]] ; then
    echo "--------- SKIPPING SCRIPT $test ---------"
    continue
  fi
  if [[ "${tests_to_ignore[*]}" =~ $test ]]; then
    echo "--------- RUNNING SCRIPT $test --- IGNORING FAILURES"
    set +e
    echo "Running ./test_unstructured_ingest/$test"
    ./test_unstructured_ingest/src/"$test"
    set -e
    echo "--------- FINISHED SCRIPT $test ---------"
  else
    echo "--------- RUNNING SCRIPT $test ---------"
    echo "Running ./test_unstructured_ingest/$test"
    ./test_unstructured_ingest/src/"$test"
    echo "--------- FINISHED SCRIPT $test ---------"
  fi
done

all_eval=(
  'text-extraction'
  'element-type'
)
for eval in "${all_eval[@]}"; do
  CURRENT_TEST="$eval"
  echo "--------- RUNNING SCRIPT $eval ---------"
  ./test_unstructured_ingest/evaluation-metrics.sh "$eval"
  echo "--------- FINISHED SCRIPT $eval ---------"
done
