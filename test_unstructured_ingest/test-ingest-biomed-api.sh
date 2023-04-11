#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

#if [[ "$(find test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api/ -type f -size +10k | wc -l)" != 2 ]]; then
#    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api/ look suspicious. At least one of the files is too small."
#    echo "Did you overwrite test fixtures with bad outputs?"
#    exit 1
#fi

PYTHONPATH=. ./unstructured/ingest/main.py \
   --metadata-exclude filename \
   --biomed-api-from "2019-01-02" \
   --biomed-api-until "2019-01-02+00:03:10" \
   --structured-output-dir biomed-ingest-output-api  \
   --num-processes 2 \
   --reprocess \
   --verbose \
   --preserve-downloads

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    find biomed-ingest-output-api/
    rsync -rlptDv --no-o --no-g biomed-ingest-output-api/ test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api

elif ! diff -ru biomed-ingest-output-api test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api ; then
    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
    echo
    echo "  export OVERWRITE_FIXTURES=true"
    echo
    echo "and then rerun this script."
    exit 1

fi
