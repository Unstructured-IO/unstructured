#!/usr/bin/env bash

# Runs a docker container to create an elasticsearch cluster,
# fills the ES cluster with data,
# processes all the files in the 'movies' index in the cluster using the `unstructured` library.

# Structured outputs are stored in elasticsearch-ingest-output

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1
echo $(pwd)


(
    echo $(pwd)
    chmod +x scripts/elasticsearch-test-helpers/create-and-check-es.sh
    . scripts/elasticsearch-test-helpers/create-and-check-es.sh

)

wait

# Read the container id from the temporary file
echo "$(pwd) before container id"
ls "examples"
ls "examples/ingest"
ls "examples/ingest/elasticsearch"
container_id=$(<"examples/ingest/elasticsearch/elasticsearch-docker_container_id.txt")
rm examples/ingest/elasticsearch/elasticsearch-docker_container_id.txt
# Kill the container so the script can be repeatedly run using the same ports
trap "docker stop $container_id" EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --elasticsearch-url http://localhost:9200 \
        --elasticsearch-index-name movies \
        --jq-query '{ethnicity, director, plot}' \
        --structured-output-dir elasticsearch-ingest-output \
        --num-processes 2
