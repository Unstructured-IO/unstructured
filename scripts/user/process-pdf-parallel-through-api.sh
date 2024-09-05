#!/usr/bin/env bash

# Usage: ./process-pdf-parallel-through-api.sh filename.pdf

set -eu -o pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <pdf_filename>"
  echo "Please provide a PDF filename as the first argument."
  echo
  echo "Optionally, set the following env vars: "
  echo
  echo "* STRATEGY (default hi_res)"
  echo "* BATCH_SIZE (default 30) as the number of parts (AKA splits) to process in parallel"
  echo "* PDF_SPLIT_PAGE_SIZE (default 10) as the number of pages per split"
  echo
  echo "BATCH_SIZE=20 PDF_SPLIT_PAGE_SIZE=6 STRATEGY=hi_res ./process-pdf-parallel-through-api.sh example-docs/pdf/layout-parser-paper.pdf"
  exit 1
fi

ALLOWED_STRATEGIES=("hi_res" "fast" "auto")

# Validate STRATEGY environment variable if it's set
if [ -n "${STRATEGY:-}" ] && [[ ! " ${ALLOWED_STRATEGIES[*]} " =~ ${STRATEGY} ]]; then
  echo "Error: STRATEGY must be one of ${ALLOWED_STRATEGIES[*]}" >&2
  exit 1
fi

# Check if PAID_UNST_API_KEY is set
if [ -z "${PAID_UNST_API_KEY}" ]; then
  echo "Error: PAID_UNST_API_KEY is not set or is empty" >&2
  exit 1
fi

PDF_FILE="$1"
DEFAULT_SPLIT_SIZE=10
SPLIT_SIZE=${PDF_SPLIT_PAGE_SIZE:-$DEFAULT_SPLIT_SIZE}
PDF_NAME=$(basename "$PDF_FILE" .pdf)
DEFAULT_DIR="$HOME/tmp/pdf-splits"
PDF_SPLITS_DIR="${PDF_SPLITS_DIR:-$DEFAULT_DIR}"
MD5_SUM=$(md5sum "$PDF_FILE" | awk '{ print $1 }')
PDF_DIR="$PDF_SPLITS_DIR/$PDF_NAME-${MD5_SUM}_split-${SPLIT_SIZE}"
PDF_OUTPUT_DIR="$PDF_SPLITS_DIR/${PDF_NAME}-output-${MD5_SUM}_split-${SPLIT_SIZE}_strat-${STRATEGY}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if PDF parts directory exists
if [ ! -d "$PDF_DIR" ]; then
  "$SCRIPT_DIR/split-pdf.sh" "$PDF_FILE"
fi

# Create output directory if it does not exist
mkdir -p "$PDF_OUTPUT_DIR"

incomplete=0 # Flag to track incomplete processing

# Function to process a single PDF part file
process_file_part() {
  local file="$1"
  local STARTING_PAGE_NUMBER="$2"
  local OUTPUT_JSON="$3"

  if [ -f "$OUTPUT_JSON" ]; then
    echo "Skipping processing for $OUTPUT_JSON as it already exists."
    return
  fi

  curl -q -X POST https://api.unstructuredapp.io/general/v0/general \
    -H "unstructured-api-key: $PAID_UNST_API_KEY" \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F strategy="${STRATEGY:-hi_res}" \
    -F 'skip_infer_table_types="[]"' \
    -F starting_page_number="$STARTING_PAGE_NUMBER" \
    -F files=@"$file;filename=$PDF_FILE" \
    -o "$OUTPUT_JSON"
  
  # Verify JSON content
  if ! jq -e 'if type=="array" then all(.[]; type=="object" or length==0) else empty end' "$OUTPUT_JSON" >/dev/null; then
    echo "Invalid JSON structure in $OUTPUT_JSON (contents below), deleting file."
    cat "$OUTPUT_JSON"
    rm "$OUTPUT_JSON"
    incomplete=1
  else
    echo "Valid JSON output created: $OUTPUT_JSON"
  fi
}

# Function to process a batch of files
process_batch() {
  for file in "$@"; do
    local START_PAGE
    START_PAGE=$(echo "$file" | sed -n 's/.*_pages_\([0-9]*\)_to_[0-9]*.pdf/\1/p')
    local END_PAGE=
    END_PAGE=$(echo "$file" | sed -n 's/.*_pages_[0-9]*_to_\([0-9]*\).pdf/\1/p')
    local OUTPUT_JSON="$PDF_OUTPUT_DIR/${PDF_NAME}_pages_${START_PAGE}_to_${END_PAGE}.json"
    process_file_part "$file" "$START_PAGE" "$OUTPUT_JSON" &
  done
  wait
}

# Read PDF parts into an array
mapfile -t pdf_parts < <(find "$PDF_DIR" -name '*.pdf' -print)

# Process PDF parts in batches of 30, by default
batch_size=${BATCH_SIZE:-30}
for ((i = 0; i < ${#pdf_parts[@]}; i+=batch_size)); do
  process_batch "${pdf_parts[@]:i:batch_size}"
done

# Determine the output filename based on whether processing was incomplete
if [ "$incomplete" -eq 1 ]; then
  combined_output_filename="${PDF_NAME}_incomplete_combined.json"
  echo "WARNING! not all json parts were successfully processed. you may rerun this script"
  echo "to attempt reprocessing those (failed to process) parts."
else
  combined_output_filename="${PDF_NAME}_combined.json"
fi

# Combine JSON outputs in numerical order
find "$PDF_OUTPUT_DIR" -name '*.json' -print0 | sort -zV | xargs -0 jq -s 'add' >"$PDF_OUTPUT_DIR/$combined_output_filename"

echo "Processing complete. Combined JSON saved to $PDF_OUTPUT_DIR/$combined_output_filename"
