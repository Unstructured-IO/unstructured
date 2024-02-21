#!/usr/bin/env bash

# Usage:
#   - Set the required environment variables (listed below)
#   - Run the script: ./scripts/performance/benchmark.sh

# Environment Variables:
#   - DOCKER_TEST: Set to "true" to run benchmark inside a Docker container (default: false)
#   - NUM_ITERATIONS: Number of iterations for benchmark (e.g., 100) (default: 3)
#   - INSTANCE_TYPE: Type of benchmark instance (e.g., "c5.xlarge") (default: "unspecified")
#   - PUBLISH_RESULTS: Set to "true" to publish results to S3 bucket (default: false)

SLOW_FILES=("DA-619p.pdf" "layout-parser-paper-hi_res-16p.pdf" "layout-parser-paper-10p.jpg")
HI_RES_STRATEGY_FILES=("layout-parser-paper-hi_res-16p.pdf")
NUM_ITERATIONS=${NUM_ITERATIONS:-2}
INSTANCE_TYPE=${INSTANCE_TYPE:-"unspecified"}

S3_BUCKET="utic-dev-tech-fixtures"
S3_RESULTS_DIR="performance-test/results"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_HASH="$(git rev-parse --short HEAD)"

# Save the results filename to a temporary file
RESULTS_FILENAME_FILE=$(mktemp)
trap 'rm -f $RESULTS_FILENAME_FILE' EXIT

function read_benchmark_logs_for_results() {
  if [[ $line =~ Results\ saved\ to:\ ([^\ ]+) ]]; then
    results_filename="${BASH_REMATCH[1]}"
    echo "CSV file value found: $results_filename"
    echo "$results_filename" >"$RESULTS_FILENAME_FILE" # Store the value in the temporary file
  fi
}

if [[ "$DOCKER_TEST" == "true" ]]; then
  DOCKER_IMAGE=unstructured:perf-test make docker-build
  docker rm -f unstructured-perf-test >/dev/null 2>&1
  docker run \
    --name unstructured-perf-test \
    --rm \
    -e NUM_ITERATIONS="$NUM_ITERATIONS" \
    -e INSTANCE_TYPE="$INSTANCE_TYPE" \
    -e GIT_HASH="$GIT_HASH" \
    -e SLOW_FILES="${SLOW_FILES[*]}" \
    -e HI_RES_STRATEGY_FILES="${HI_RES_STRATEGY_FILES[*]}" \
    -v "${SCRIPT_DIR}":/home/notebook-user/scripts/performance \
    unstructured:perf-test \
    bash /home/notebook-user/scripts/performance/benchmark-local.sh 2>&1 | tee >(while IFS= read -r line; do
      read_benchmark_logs_for_results
    done)
else
  NUM_ITERATIONS="$NUM_ITERATIONS" INSTANCE_TYPE="$INSTANCE_TYPE" GIT_HASH="$GIT_HASH" SLOW_FILES="${SLOW_FILES[*]}" HI_RES_STRATEGY_FILES="${HI_RES_STRATEGY_FILES[*]}" "$SCRIPT_DIR"/benchmark-local.sh 2>&1 |
    tee >(while IFS= read -r line; do
      read_benchmark_logs_for_results
    done)
fi
# Read the result filename from the temporary file
results_filename=$(<"$RESULTS_FILENAME_FILE")
if [[ -z $results_filename ]]; then
  echo "Error: Results filename value not found in the benchmark logs."
  exit 1
fi
if [[ "$PUBLISH_RESULTS" == "true" ]]; then
  S3_RESULTS_PATH="$S3_BUCKET/$S3_RESULTS_DIR"
  echo "Publishing results to S3 bucket: $S3_RESULTS_PATH"
  aws s3 cp "$SCRIPT_DIR/benchmark_results/$results_filename" "s3://$S3_RESULTS_PATH/"
fi
