#!/usr/bin/env bash

unstructured-ingest \
  mongodb \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --uri "<MongoDB uri>" \
  --database "<MongoDB Database Name>" \
  --collection "<MongoDB Collection name>" \
  --output-dir mongodb-ingest-output \
  --num-processes 2
