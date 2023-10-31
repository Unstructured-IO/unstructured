#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

all_tests=(
'azure.sh'
'box.sh'
'dropbox.sh'
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

tests_to_ignore=()

for test in "${all_tests[@]}"; do
  CURRENT_TEST="$test"
  if [[ "${tests_to_ignore[*]}" =~ $test ]]; then
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
