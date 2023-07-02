#!/usr/bin/env bash

# Runs a docker container to create an elasticsearch cluster,
# fills the ES cluster with data,
# processes all the files in the 'movies' index in the cluster using the `unstructured` library.

# Structured outputs are stored in elasticsearch-ingest-output

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# shellcheck source=/dev/null
sh scripts/elasticsearch-test-helpers/create-and-check-es.sh
wait

# Kill the container so the script can be repeatedly run using the same ports
trap 'echo "Stopping Elasticsearch Docker container"; docker stop es-test' EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --elasticsearch-url http://localhost:9200 \
        --elasticsearch-index-name movies \
        --jq-query '{ethnicity, director, plot}' \
        --structured-output-dir elasticsearch-ingest-output \
        --num-processes 2
