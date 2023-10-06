#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# NOTE(crag): sets number of tesseract threads to 1 which may help with more reproducible outputs
export OMP_THREAD_LIMIT=1

scripts=(
'test-ingest-salesforce.sh'
)

CURRENT_SCRIPT="none"

function print_last_run() {
  if [ "$CURRENT_SCRIPT" != "none" ]; then
    echo "Last ran script: $CURRENT_SCRIPT"
  fi
}

trap print_last_run EXIT

for script in "${scripts[@]}"; do
  CURRENT_SCRIPT=$script
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
    ./test_unstructured_ingest/"$script"
    echo "--------- FINISHED SCRIPT $script ---------"
  fi
done
