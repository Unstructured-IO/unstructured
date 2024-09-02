#!/usr/bin/env bash

# Usage: ./split_pdf.sh filename.pdf

set -e

PDF_FILE="$1"
DEFAULT_SPLIT_SIZE=5
SPLIT_SIZE=${PDF_SPLIT_PAGE_SIZE:-$DEFAULT_SPLIT_SIZE}

# Validate that SPLIT_SIZE is an integer
if ! [[ "$SPLIT_SIZE" =~ ^[0-9]+$ ]]; then
  echo "Error: PDF_SPLIT_PAGE_SIZE must be an integer."
  exit 1
fi

DEFAULT_DIR="$HOME/tmp/pdf-splits"
PDF_SPLITS_DIR="${PDF_SPLITS_DIR:-$DEFAULT_DIR}"
PDF_NAME=$(basename "$PDF_FILE" .pdf)
MD5_SUM=$(md5sum "$PDF_FILE" | awk '{ print $1 }')
PDF_DIR="$PDF_SPLITS_DIR/$PDF_NAME-${MD5_SUM}_split-${SPLIT_SIZE}"

# Create directory if it does not exist
mkdir -p "$PDF_DIR"

# Total number of pages
TOTAL_PAGES=$(qpdf --show-npages "$PDF_FILE")

# Split PDF into $SPLIT_SIZE-page chunks
START_PAGE=1
while [ $START_PAGE -le $TOTAL_PAGES ]; do
  END_PAGE=$((START_PAGE + SPLIT_SIZE - 1))
  if [ $END_PAGE -gt $TOTAL_PAGES ]; then
    END_PAGE=$TOTAL_PAGES
  fi
  OUTPUT_FILE="$PDF_DIR/${PDF_NAME}_pages_${START_PAGE}_to_${END_PAGE}.pdf"
  qpdf "$PDF_FILE" --pages . $START_PAGE-$END_PAGE -- "$OUTPUT_FILE"
  echo "Created $OUTPUT_FILE"
  START_PAGE=$((END_PAGE + 1))
done

echo "All parts have been saved to $PDF_DIR"
