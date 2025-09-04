#!/bin/bash

# Define the input and output top directories
SCRIPT_DIR=$(dirname "$(realpath "$0")")
OUTPUT_DIR=${1:-"$SCRIPT_DIR/structured-output-markdown"}
INPUT_DIR="$SCRIPT_DIR/expected-structured-output"
PYTHON_SCRIPT="$SCRIPT_DIR/../scripts/convert/elements_json_to_format.py"
EXCLUDE_IMG=0
NO_GROUP=1

# Function to process JSON files
process_json_files() {
  # Add flags based on the variables
  cmd="PYTHONPATH=${PYTHONPATH:-.} python \"$PYTHON_SCRIPT\" \"$INPUT_DIR\" --outdir \"$OUTPUT_DIR\" --format markdown"
  if [ "$EXCLUDE_IMG" -eq 1 ]; then
    cmd+=" --exclude-img"
  fi
  if [ "$NO_GROUP" -eq 1 ]; then
    cmd+=" --no-group"
  fi
  # Run the Python script with the constructed command
  eval "$cmd"
}

# Start processing from the input directory
process_json_files
