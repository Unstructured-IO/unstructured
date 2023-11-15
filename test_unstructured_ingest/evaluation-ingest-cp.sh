#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_DIR=$1
OUTPUT_FOLDER_NAME=$2

function walk_dir() {
  local directory=$1
  local -a walkdir=()

  while IFS= read -r -d '' file; do
    walkdir+=("$file")
  done < <(find "$directory" -type f -name "*.json" -print0 | sed -z "s|${directory}/||")

  echo "${walkdir[@]}"
}

structured_outputs=()
while IFS= read -r -d $'\0' line; do
    structured_outputs+=("$line")
done < <(walk_dir "$OUTPUT_DIR")

OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
CP_DIR=$OUTPUT_ROOT/structured-output-eval/$OUTPUT_FOLDER_NAME
mkdir -p "$CP_DIR"

selected_outputs=$(cat "$SCRIPT_DIR/metrics/metrics-json-manifest.txt")

# If structured output file in this connector's outputs match the
# selected outputs in the txt file, copy to the destination
for file in "${structured_outputs[@]}"; do
  if [[ "${selected_outputs[*]}" =~ $(basename "$file") ]] ; then
    echo "--- Copying $OUTPUT_DIR/$file to $CP_DIR/$file ---"
    cp -n "$OUTPUT_DIR/$file" "$CP_DIR"
  fi
done
