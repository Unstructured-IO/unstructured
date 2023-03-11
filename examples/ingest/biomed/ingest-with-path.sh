***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the Unstructured-IO/unstructured repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in biomed-ingest-output-path/

***REMOVED*** Biomedical documents can be extracted in one of two ways, in this script is the FTP directory approach.

***REMOVED*** The supported ftp directories is:
***REMOVED*** https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf

***REMOVED*** By providing the path, the documents existing therein are downloaded.
***REMOVED*** For example, to download the documents in the path: https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/07/
***REMOVED*** The path needed is oa_pdf/07/


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

***REMOVED*** The example below will ingest the PDF from the "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" path.

***REMOVED*** You can ingest all the documents in the "oa_pdf/07/07" path by passing "oa_pdf/07/07" instead.
***REMOVED*** WARNING: There are many documents in that path.

PYTHONPATH=. ./unstructured/ingest/main.py \
    --biomed-path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
    --structured-output-dir biomed-ingest-output-path \
    --num-processes 2 \
    --verbose \
    --preserve-downloads

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --biomed-path ...
