#!/bin/bash

# Set the S3 bucket and key for the zip file
S3_BUCKET='utic-dev-tech-fixtures'
ZIP_FILE="benchmark/benchmark-docs.zip"

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the folder name for decompression and benchmarking as a sibling of the script
DECOMPRESSED_FOLDER="$SCRIPT_DIR/benchmark-docs"

# Set the list of slow files
SLOW_FILES=("slow_file1.txt" "slow_file2.txt")

# Set the number of iterations for averaging
NUM_ITERATIONS=${NUM_ITERATIONS:-5}

# Set the publish results flag and S3 folder
PUBLISH_RESULTS=true
RESULTS_FOLDER="results"

# Set the instance type
INSTANCE_TYPE=${INSTANCE_TYPE:-"unspecified"}



# Function to convert date to Unix timestamp
convert_to_timestamp() {
  if [[ "$(uname)" == "Darwin" ]]; then
    date -j -f "%Y-%m-%d" "$1" "+%s"
  else
    date -d "$1" "+%s"
  fi
}

# Echo folder creation timestamp
if [[ "$(uname)" == "Darwin" ]]; then
  FOLDER_TIMESTAMP=$(stat -f "%B" -t "%Y-%m-%d" "$DECOMPRESSED_FOLDER")
else
  FOLDER_TIMESTAMP=$(stat -c "%Y" "$DECOMPRESSED_FOLDER")
fi

# Check if the 'date' command supports the '-d' option
if date -d "-1 day" >/dev/null 2>&1; then
  FOLDER_TIMESTAMP=$(date -d @"$FOLDER_TIMESTAMP" "+%Y-%m-%d %H:%M:%S")
else
  FOLDER_TIMESTAMP=$(date -r "$FOLDER_TIMESTAMP" "+%Y-%m-%d %H:%M:%S")
fi
echo "Folder Creation Timestamp: $FOLDER_TIMESTAMP"

# Echo S3 zip creation timestamp
ZIP_TIMESTAMP=$(aws s3 ls "s3://$S3_BUCKET/$ZIP_FILE" --recursive | awk '{print $1, $2}')
echo "S3 Zip Creation Timestamp: $ZIP_TIMESTAMP"

# Check if the decompressed folder needs to be updated
if [[ ! -d "$DECOMPRESSED_FOLDER" || "$1" == "--force-download" || \
   "$ZIP_TIMESTAMP" > "$FOLDER_TIMESTAMP" ]]; then
    echo "Updating decompressed folder..."
    rm -rf "$DECOMPRESSED_FOLDER"
    aws s3 cp "s3://$S3_BUCKET/$ZIP_FILE" "$SCRIPT_DIR/"
    mkdir -p "$DECOMPRESSED_FOLDER"
    unzip -qj "$SCRIPT_DIR/$(basename "$ZIP_FILE")" -d "$DECOMPRESSED_FOLDER"
fi


# stats-name="$SCRIPT_DIR/get-stats-name.sh"
# docker exec -it <container_name> "$SCRIPT_DIR/get-stats-name.sh"

# # Create the CSV file for output
# DATE=$(date +"%Y-%m-%d_%H-%M-%S")
# CSV_FILE="$SCRIPT_DIR/${DATE}_benchmark_results.csv"
# echo "Test File,Iterations,Execution Time (s)" > "$CSV_FILE"

# # Iterate through each file in the decompressed folder
# for file in "$TEST_DOCS_FOLDER"/*; do
#     echo "Running benchmark for file: $file"

#     # Check if the file is in the slow files list
#     if [[ " ${SLOW_FILES[@]} " =~ " $(basename "$file") " ]]; then
#         echo "File found in slow files list. Running once..."
#         num_iterations=1
#     else
#         num_iterations=$NUM_ITERATIONS
#     fi

#     total_execution_time=0

#     for ((i = 1; i <= num_iterations; i++)); do
#         echo "Iteration $i"
        
#         # Run the test function and measure execution time
#         start_time=$(date +%s.%N)
#         # Replace `your_test_function` with the actual function you want to run
#         your_test_function "$file"
#         end_time=$(date +%s.%N)
#         execution_time=$(echo "$end_time - $start_time" | bc)

#         # Add execution time to the total
#         total_execution_time=$(echo "$total_execution_time + $execution_time" | bc)
#     done

#     # Calculate average execution time
#     average_execution_time=$(echo "scale=2; $total_execution_time / $num_iterations" | bc)

#     # Append the benchmark results to the CSV file
#     echo "$file,$num_iterations,$average_execution_time" >> "$CSV_FILE"
# done

# echo "Benchmarking completed. Results saved to $CSV_FILE"

# # Publish results to S3 if enabled
# if [ "$PUBLISH_RESULTS" = true ]; then
#     RESULTS_BUCKET="$S3_BUCKET/$RESULTS_FOLDER"
#     echo "Publishing results to S3 bucket: $RESULTS_BUCKET"
#     aws s3 cp "$CSV_FILE" "s3://$RESULTS_BUCKET/${DATE}_benchmark_results_${INSTANCE_TYPE}_$(get-stats-name).csv"
# fi
