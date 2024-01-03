#!/usr/bin/env bash

unstructured-ingest \
  elasticsearch \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url http://localhost:9200 \
  --index-name movies \
  --fields 'ethnicity, director, plot' \
  --output-dir elasticsearch-ingest-output \
  --num-processes 2
