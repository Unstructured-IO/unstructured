#!/usr/bin/env bash

unstructured-ingest \
  opensearch \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url http://localhost:9200 \
  --index-name movies \
  --fields 'ethnicity, director, plot' \
  --output-dir opensearch-ingest-output \
  --num-processes 2
