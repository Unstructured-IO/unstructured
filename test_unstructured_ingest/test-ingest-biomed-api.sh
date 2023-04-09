#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api/ -type f -size +10k | wc -l)" != 2 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
   --metadata-exclude filename \
   --biomed-api-from "2019-01-02" \
   --biomed-api-until "2019-01-02+00:03:10" \
   --structured-output-dir biomed-ingest-output-api  \
   --num-processes 2 \
   --verbose \
   --download-dir biomed-download-api \
   --preserve-downloads

if ! diff -ru biomed-ingest-output-api test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "biomed-ingest-output-api/ to test_unstructured_ingest/expected-structured-output/biomed-ingest-output-api/ after running"
   echo 
   echo "PYTHONPATH=. ./unstructured/ingest/main.py --biomed-api-from '2019-01-02' --biomed-api-until '2019-01-02+00:03:10' --structured-output-dir biomed-ingest-output-api --num-processes 2 --verbose --download-dir biomed-download-api --preserve-downloads"
   echo
   exit 1
fi
