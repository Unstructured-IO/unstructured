#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_DIR=$1
OUTPUT_FOLDER_NAME=$2
structured_outputs=("$OUTPUT_DIR"/*)

CP_DIR=$SCRIPT_DIR/structured-output-eval/$OUTPUT_FOLDER_NAME
mkdir -p "$CP_DIR"

selected_outputs=$(cat "$SCRIPT_DIR/metrics/metrics-json-manifest.txt")

# If structured output file in this connector's outputs match the 
# selected outputs in the txt file, copy to the destination
for file in "${structured_outputs[@]}"; do
  if [[ "${selected_outputs[*]}" =~ $(basename "$file") ]] ; then
    echo "--- Copying $file to $CP_DIR ---"
    cp "$file" "$CP_DIR"
  fi
done 
