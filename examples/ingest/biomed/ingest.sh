#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in biomed-ingest-output/

# Biomedical documents can be extracted in one of two ways:

# FIRST APPROACH

# Through the ftp directories:
# https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf
# https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package

# By providing the path, the documents existing therein are downloaded.
# For example, to download the documents in the path: https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/07/
# The path needed is oa_pdf/07/

# To download the documents in the path: https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/0a/01/
# The path needed is oa_package/0a/01/

# SECOND APPROACH

# Through the OA Web Service API and the parameters provided here: https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/

# For example, to download documents from 2019-01-02 00:00:00 to 2019-01-02+00:03:10"
# the parameters "from" and "until" are needed

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --biomed-api-from "2019-01-02" \
    --biomed-api-until "2019-01-02+00:03:10" \
    --biomed-api-format "pdf" \
    --structured-output-dir biomed-ingest-output \
    --num-processes 2 \
    --verbose \
    --download-dir biomed-download \
    --preserve-downloads
#    --biomed-path "oa_pdf/07/07" # Uses the FTP directory path instead of API.


# Alternatively, you can call it using:
# unstructured-ingest --drive-id ...
