#!/usr/bin/env bash

# This is intended solely to be called by scripts/performance/benchmark.sh.
# This file is separated out to allow us to easily execute this part of the test script inside a Docker container.

SCRIPT_DIR=$(dirname "$0")
TEST_DOCS_FOLDER="$SCRIPT_DIR/docs"
TIMEFORMAT="%R"

mkdir -p "$SCRIPT_DIR/benchmark_results" >/dev/null 2>&1
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
RESULTS_FILE="$SCRIPT_DIR/benchmark_results/${DATE}_benchmark_results_${INSTANCE_TYPE}_$("$SCRIPT_DIR/get-stats-name.sh")_$GIT_HASH.csv"
echo "Test File,Iterations,Average Execution Time (s)" >"$RESULTS_FILE"

echo "Starting benchmark test..."
for file in "$TEST_DOCS_FOLDER"/*; do
  echo "Testing file: $(basename "$file")"

  if [[ " ${SLOW_FILES[*]} " =~ $(basename "$file") ]]; then
    echo "File found in slow files list. Running once..."
    num_iterations=1
  else
    # shellcheck disable=SC2153
    num_iterations=$NUM_ITERATIONS
  fi

  strategy="fast"
  if [[ " ${HI_RES_STRATEGY_FILES[*]} " =~ $(basename "$file") ]]; then
    echo "Testing with hi_res strategy"
    strategy="hi_res"
  fi
  if ! response=$(python3 -m "scripts.performance.time_partition" "$file" "$num_iterations" "$strategy"); then
    echo "error: $response"
    exit 1
  fi
  average_time=$(echo "$response" | awk '/Average time:/ {print $3}')
  echo "Average execution time: $average_time seconds"
  echo "$(basename "$file"),$num_iterations,$average_time" >>"$RESULTS_FILE"
done

# NOTE: Be careful if updating this message. The benchmarking script looks for this message to get the CSV file name.
echo "Benchmarking completed. Results saved to: $(basename "$RESULTS_FILE")"
