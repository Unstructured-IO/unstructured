#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

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

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp -R elasticsearch-ingest-output/* test_unstructured_ingest/expected-structured-output/elasticsearch-ingest-output/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/elasticsearch-ingest-output elasticsearch-ingest-output ; then
    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
    echo
    echo "  export OVERWRITE_FIXTURES=true"
    echo
    echo "and then rerun this script."
    echo
    echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
    echo "to update fixtures for CI."
    echo
    exit 1

fi
