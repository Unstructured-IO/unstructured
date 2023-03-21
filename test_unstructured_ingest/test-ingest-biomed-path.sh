***REMOVED***!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/biomed-ingest-output-path/ -type f -size +10k | wc -l)" != 1 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/biomed-ingest-output-path/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --biomed-path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
    --structured-output-dir biomed-ingest-output-path \
    --num-processes 2 \
    --verbose \
    --download-dir biomed-download-path \
    --preserve-downloads


if ! diff -ru biomed-ingest-output-path test_unstructured_ingest/expected-structured-output/biomed-ingest-output-path ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "biomed-ingest-output-path/ to test_unstructured_ingest/expected-structured-output/biomed-ingest-output-path/ after running"
   echo 
   echo "PYTHONPATH=. ./unstructured/ingest/main.py --biomed-path 'oa_pdf/07/07/sbaa031.073.PMC7234218.pdf' --structured-output-dir biomed-ingest-output-path --num-processes 2 --verbose --download-dir biomed-download-path --preserve-downloads"
   echo
   exit 1
fi
