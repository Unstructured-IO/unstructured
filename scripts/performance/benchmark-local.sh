#!/bin/bash

SLOW_FILES=("book-war-and-peace.txt")
HI_RES_STRATEGY_FILES=("layout-parser-paper.pdf")
NUM_ITERATIONS=${NUM_ITERATIONS:-2}
INSTANCE_TYPE=${INSTANCE_TYPE:-"unspecified"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DOCS_FOLDER="$SCRIPT_DIR/docs"
TIMEFORMAT="%R"

function process_file() {
    filepath=$1
    strategy=$2
    python3.8 -c 'from unstructured.partition.auto import partition; partition("'"$filepath"'", strategy="'"$strategy"'")[3]'
}

mkdir -p "$SCRIPT_DIR/results" > /dev/null 2>&1
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
RESULTS_FILE="$SCRIPT_DIR/results/${DATE}_benchmark_results_${INSTANCE_TYPE}_$("$SCRIPT_DIR/get-stats-name.sh")_$(git rev-parse --short HEAD).csv"
echo "Test File,Iterations,Average Execution Time (s)" > "$RESULTS_FILE"

echo "Warming up..."
process_file "$SCRIPT_DIR/warmup.pdf" "hi_res" > /dev/null

echo "Starting benchmark test..."
for file in "$TEST_DOCS_FOLDER"/*; do
    echo "Testing file: $(basename "$file")"

    if [[ " ${SLOW_FILES[@]} " =~ " $(basename "$file") " ]]; then
        echo "File found in slow files list. Running once..."
        num_iterations=1
    else
        num_iterations=$NUM_ITERATIONS
    fi
    total_execution_time=0
    for ((i = 1; i <= num_iterations; i++)); do
        echo "Iteration $i"
        strategy="fast"
        if [[ " ${HI_RES_STRATEGY_FILES[@]} " =~ " $(basename "$file") " ]]; then
            echo "Using hi res"
            strategy="hi_res"
        fi
        response=$( { time process_file "$file" "$strategy"; } 2>&1 )
        if [[ $? -ne 0 ]]; then
            echo "error: $response"
            exit 1
        fi
        echo "$response"
        time_response=$(echo "$response" | awk 'END { print }')
        echo "Execution time: $time_response"
        total_execution_time=$(echo "$total_execution_time + $time_response" | bc)

    done
    average_time_seconds=$(echo "scale=3; $total_execution_time / $num_iterations" | bc)
    echo "Average execution time: $average_time_seconds"
    echo "$(basename "$file"),$num_iterations,$average_time_seconds" >> "$RESULTS_FILE"
done

# NOTE: Be careful if updating this message. The benchmarking script looks for this message to get the CSV file name.
echo "Benchmarking completed. Results saved to: $(basename "$RESULTS_FILE")"


