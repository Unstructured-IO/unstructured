#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

all_tests=(
  'azure.sh'
  'azure-cognitive-search.sh'
  'box.sh'
  'delta-table.sh'
  'dropbox.sh'
  'gcs.sh'
  'mongodb.sh'
  's3.sh'
  'weaviate.sh'
  'sharepoint-embed-cog-index.sh'
)

full_python_matrix_tests=(
  'azure.sh'
  'gcs.sh'
  's3.sh'
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
    ./test_unstructured_ingest/dest/"$test"
    set -e
    echo "--------- FINISHED SCRIPT $test ---------"
  else
    echo "--------- RUNNING SCRIPT $test ---------"
    echo "Running ./test_unstructured_ingest/$test"
    ./test_unstructured_ingest/dest/"$test"
    echo "--------- FINISHED SCRIPT $test ---------"
  fi
done
