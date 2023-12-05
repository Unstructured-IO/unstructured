#!/usr/bin/env bash
# shellcheck disable=SC2154

set -u -o pipefail

# Run general checks
if [ $# -ne 2 ]; then
  echo "usage: $0 [src|dest] [core|non-core|all]"
  exit 1
fi
if [[ ! "src dest" =~ $1 ]]; then
  echo "not a recognized test type ([src|dest]): $1)"
  exit 1
fi
if [[ ! "core non-core all" =~ $2 ]]; then
  echo "not a recognized core type ([core|non-core|all]): $2)"
  exit 1
fi

test_type=$1
core_type=$2

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SKIPPED_FILES_LOG=$SCRIPT_DIR/skipped-files.txt
# If the file already exists, reset it
if [ -f "$SKIPPED_FILES_LOG" ]; then
  rm "$SKIPPED_FILES_LOG"
fi
touch "$SKIPPED_FILES_LOG"
cd "$SCRIPT_DIR"/.. || exit 1
CURRENT_TEST="none"

# Pull in variables specific to each
# shellcheck disable=SC1090
source "$SCRIPT_DIR"/test-ingest-configs-"$test_type".sh


get_tests() {
  local -n arr=$1
  if [ "$core_type" == "all" ]; then
    echo "Setting all $test_type tests"
    all_tests=$(ls "$SCRIPT_DIR"/"$test_type"/)
    arr="${all_tests[*]}"
  elif [ "$core_type" != "core" ]; then
    echo "setting non core $test_type tests"
    all_tests=$(ls "$SCRIPT_DIR"/"$test_type"/)
    diff=$(echo "${all_tests[@]}" "${core_tests[@]}" | tr ' ' '\n' | sort | uniq -u)
    arr="${diff[*]}"
  else
    echo "setting core $test_type tests"
    # shellcheck disable=SC2034
    arr="${core_tests[*]}"
  fi
}


function log_results() {
  if [ "$CURRENT_TEST" != "none" ]; then
    echo "Last ran script: $CURRENT_TEST"
  fi
  echo "######## SKIPPED TESTS: ########"
  cat "$SKIPPED_FILES_LOG"
}

trap log_results EXIT

run_tests() {
  local tests_to_run
  get_tests tests_to_run
  for test in $tests_to_run; do
    CURRENT_TEST="$test"
    echo "--------- RUNNING SCRIPT $test ---------"
    echo "Running ./test_unstructured_ingest/$test_type/$test"
    ./test_unstructured_ingest/"$test_type"/"$test"
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
}

run_evals() {
  for eval in "${all_eval[@]}"; do
    CURRENT_TEST="evaluation-metrics.sh $eval"
    echo "--------- RUNNING SCRIPT evaluation-metrics.sh $eval ---------"
    ./test_unstructured_ingest/evaluation-metrics.sh "$eval"
    echo "--------- FINISHED SCRIPT evaluation-metrics.sh $eval ---------"
  done
}

run_tests