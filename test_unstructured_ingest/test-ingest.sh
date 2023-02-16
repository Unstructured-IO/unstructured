#!/usr/bin/env bash

set -eux -o pipefail

if [[ "$(find test_unstructured_ingest/expected-structured-output -type f -size +20k | wc -l)" != 3 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

PYTHONPATH=. python examples/ingest/s3-small-batch/main.py --anonymous --structured-output-dir s3-small-batch-output

if ! diff -ru s3-small-batch-output test_unstructured_ingest/expected-structured-output/s3-small-batch ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "s3-small-batch-output/ to test_unstructured_ingest/expected-structured-output/s3-small-batch/ after running"
   echo 
   echo "  PYTHONPATH=. python examples/ingest/s3-small-batch/main.py --structured-output-dir s3-small-batch-output"
   echo
   exit 1
fi
