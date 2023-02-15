#!/usr/bin/env bash

set -eux -o pipefail

PYTHONPATH=. python examples/ingest/s3-small-batch/main.py

if ! diff -ru structured-output/ test_unstructured_ingest/expected-structured-output/ ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "structured-ouput/ to test_unstructured_ingest/expected-structured-output after running"
   echo
   echo "  PYTHONPATH=. python examples/ingest/s3-small-batch/main.py"
   echo
   exit 1
fi
