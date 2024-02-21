#!/usr/bin/env bash

unstructured-ingest \
  biomed \
  --path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
  --output-dir biomed-ingest-output-path \
  --num-processes 2 \
  --verbose \
  --preserve-downloads
