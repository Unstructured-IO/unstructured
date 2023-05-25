#!/bin/bash

# Usage: 
#   - Set the required environment variables (listed below)
#   - Run the script: ./benchmark.sh

# Environment Variables:
#   - DOCKER_TEST: Set to "true" to run benchmark inside a Docker container (default: "false")
#   - NUM_ITERATIONS: Number of iterations for benchmark (e.g., 100) (default: 3)
#   - INSTANCE_TYPE: Type of benchmark instance (e.g., "c5.xlarge") (default: "unspecified")
#   - PUBLISH_RESULTS: Set to "true" to publish results to S3 bucket (default: "false")

S3_BUCKET="utic-dev-tech-fixtures"
S3_RESULTS_DIR="performance-test/results"
S3_DOCS_DIR="performance-test/docs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

aws s3 sync "s3://$S3_BUCKET/$S3_DOCS_DIR" "$SCRIPT_DIR/docs" --delete
# "$SCRIPT_DIR/download-test-docs.sh"

# Save the results filename to a temporary file
RESULTS_FILENAME_FILE=$(mktemp)
trap "rm -f $RESULTS_FILENAME_FILE" EXIT

function read_benchmark_logs_for_results() {
    if [[ $line =~ Results\ saved\ to:\ ([^\ ]+) ]]; then
        results_filename="${BASH_REMATCH[1]}"
        echo "CSV file value found: $results_filename"
        echo "$results_filename" > "$RESULTS_FILENAME_FILE"  # Store the value in the temporary file
    fi
}

if [[ "$DOCKER_TEST" == "true" ]]; then
    trap "docker rm -f unstructured-perf-test > /dev/null" EXIT
    DOCKER_IMAGE=unstructured:perf-test make docker-build 
    docker run \
    --name unstructured-perf-test \
    -e NUM_ITERATIONS="$NUM_ITERATIONS" \
    -e INSTANCE_TYPE="$INSTANCE_TYPE" \
    -v "${SCRIPT_DIR}":/home/scripts/performance \
    unstructured:perf-test \
    bash /home/scripts/performance/benchmark-local.sh 2>&1 | tee >(while IFS= read -r line; do
        read_benchmark_logs_for_results
    done)
else
    NUM_ITERATIONS="$NUM_ITERATIONS" INSTANCE_TYPE="$INSTANCE_TYPE" "$SCRIPT_DIR"/benchmark-local.sh 2>&1 | \
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
    aws s3 cp "$SCRIPT_DIR/results/$results_filename" "s3://$S3_RESULTS_PATH/"
fi
