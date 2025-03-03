#!/bin/bash

# Define the input and output top directories
OUTPUT_DIR=${1:-"test_unstructured_ingest/structured-output-html"}
INPUT_DIR="test_unstructured_ingest/expected-structured-output"
PYTHON_SCRIPT="scripts/html/elements_json_to_html.py"
EXCLUDE_IMG=0
NO_GROUP=1

# Function to process JSON files
process_json_files() {
    # Add flags based on the variables
    cmd="python \"$PYTHON_SCRIPT\" \"$INPUT_DIR\" --outdir \"$OUTPUT_DIR\""
    if [ "$EXCLUDE_IMG" -eq 1 ]; then
        cmd+=" --exclude-img"
    fi
    if [ "$NO_GROUP" -eq 1 ]; then
        cmd+=" --no-group"
    fi
    # Run the Python script with the constructed command
    eval $cmd
}

# Start processing from the input directory
process_json_files
