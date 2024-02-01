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
  'azure.sh'
  'azure-cognitive-search.sh'
  'box.sh'
  'chroma.sh'
  'delta-table.sh'
  'dropbox.sh'
  'elasticsearch.sh'
  'gcs.sh'
  'mongodb.sh'
  'pgvector.sh'
  'pinecone.sh'
  'qdrant.sh'
  's3.sh'
  'sharepoint-embed-cog-index.sh'
  'sqlite.sh'
  'vectara.sh'
  'weaviate.sh'
  'opensearch.sh'
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
  echo "######## SKIPPED TESTS: ########"
  cat "$SKIPPED_FILES_LOG"
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
  if [[ "$python_version" != "Python 3.10"* ]] && [[ ! "${full_python_matrix_tests[*]}" =~ $test ]]; then
    echo "--------- SKIPPING SCRIPT $test ---------"
    continue
  fi
  echo "--------- RUNNING SCRIPT $test ---------"
  echo "Running ./test_unstructured_ingest/$test"
  ./test_unstructured_ingest/dest/"$test"
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
