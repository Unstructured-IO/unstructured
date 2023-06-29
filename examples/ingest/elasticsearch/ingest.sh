#!/usr/bin/env bash

# Runs a docker container to create an elasticsearch cluster,
# fills the ES cluster with data,
# processes all the files in the 'movies' index in the cluster using the `unstructured` library.

# Structured outputs are stored in elasticsearch-ingest-output

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

id_log_filepath="scripts/elasticsearch-test-helpers/elasticsearch-docker_container_id.txt"

(
    chmod +x scripts/elasticsearch-test-helpers/create-and-check-es.sh
    . scripts/elasticsearch-test-helpers/create-and-check-es.sh

)

wait

# Read the container id from the temporary file
container_id=$(<"$id_log_filepath")
rm "$id_log_filepath"
# Kill the container so the script can be repeatedly run using the same ports
trap 'docker stop "$container_id"' EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --elasticsearch-url http://localhost:9200 \
        --elasticsearch-index-name movies \
        --jq-query '{ethnicity, director, plot}' \
        --structured-output-dir elasticsearch-ingest-output \
        --num-processes 2
