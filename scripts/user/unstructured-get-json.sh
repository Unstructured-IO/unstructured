#!/usr/bin/env bash

# TODO's
# * ability to set file type so that is not inferred by the unstructured api service
#     e.g. "-F 'files=@foo.pdf;type=application/pdf'
#

set -e

# shellcheck disable=SC2016
USAGE_MESSAGE="Usage: $0 [options] <file>"'

Options:
  --api-key KEY   Specify the API key for authentication. Set the env var $UNST_API_KEY to skip providing this option.
  --hi-res        hi_res strategy: Enable high-resolution processing, with layout segmentation and OCR
  --fast          fast strategy: No OCR, just extract embedded text
  --ocr-only      ocr_only strategy: Perform OCR (Optical Character Recognition) only. No layout segmentation.
  --tables        Enable table extraction: tables are represented as html in metadata
  --coordinates   Include coordinates in the output
  --trace         Enable trace logging for debugging, useful to cut and paste the executed curl call
  --verbose       Enable verbose logging including printing first 8 elements to stdout
  --s3            Write the resulting output to s3 (like a pastebin)
  --help          Display this help and exit.

Arguments:
  <file>          File to send to the API.

The script requires a <file>, the document to post to the Unstructured API.
The .json result is written to ~/tmp/unst-outputs/ -- this path is echoed and copied to your clipboard.
'

if [ "$#" -eq 0 ]; then
  echo "$USAGE_MESSAGE"
  exit 1
fi

API_KEY=${UNST_API_KEY:-""}
API_ENDPOINT=${UNST_API_ENDPOINT:-"https://api.unstructured.io/general/v0/general"}
TMP_DOWNLOADS_DIR="$HOME/tmp/unst-downloads"
TMP_OUTPUTS_DIR="$HOME/tmp/unst-outputs"
# only applicable if writing .json output files to S3 when using --s3, e.g. s3://bucket-name/path/
S3_URI_PREFIX=${UNST_S3_JSON_OUTPUT_URI:-""}
# e.g. us-east-2, used to provide http links for above location
S3_REGION=${UNST_S3_JSON_OUTPUT_REGION:-""}

mkdir -p "$TMP_DOWNLOADS_DIR"
mkdir -p "$TMP_OUTPUTS_DIR"

copy_to_clipboard() {
  if [ "$(uname)" == "Darwin" ]; then
    # Join all arguments into a single string and copy to clipboard
    echo "$*" | pbcopy
    echo "copied to clipboard!"
  fi
  # TODO: add clipboard support for other OS's
}

HI_RES=false
FAST=false
OCR_ONLY=false
STRATEGY=""
VERBOSE=false
TRACE=false
COORDINATES=false
TABLES=true
S3=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
  --hi-res)
    HI_RES=true
    shift
    ;;
  --fast)
    FAST=true
    shift
    ;;
  --ocr-only)
    OCR_ONLY=true
    shift
    ;;
  --trace)
    TRACE=true
    shift
    ;;
  --verbose)
    VERBOSE=true
    shift
    ;;
  --s3)
    S3=true
    shift
    ;;
  --tables)
    TABLES=true
    shift
    ;;
  --coordinates)
    COORDINATES=true
    shift
    ;;
  --api-key)
    if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
      API_KEY=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
    ;;
  --help)
    echo "$USAGE_MESSAGE"
    exit 0
    ;;
  *)
    INPUT="$1"
    shift
    ;;
  esac
done

if [ -z "$INPUT" ]; then
  echo "Error: File or URL argument is missing."
  exit 1
fi

if $TRACE; then
  set -x
fi

if [[ "$INPUT" =~ ^https?:// ]]; then
  FILENAME=$(basename "$INPUT")
  if $VERBOSE; then echo "Downloading $FILENAME $INPUT to "; fi
  INPUT_FILEPATH=${TMP_DOWNLOADS_DIR}/${FILENAME}
  curl -q -o "${OUTPUT_FILEPATH}" "$INPUT"
  echo "Downloaded file to ${OUTPUT_FILEPATH}"
else
  FILENAME=$(basename "$INPUT")
  INPUT_FILEPATH=${INPUT}
fi

if $HI_RES; then
  if $VERBOSE; then echo "Sending API request with hi_res strategy"; fi
  STRATEGY="-hi-res"
  JSON_OUTPUT_FILEPATH=${TMP_OUTPUTS_DIR}/${FILENAME}${STRATEGY}.json
  CURL_STRATEGY=(-F "strategy=hi_res")
elif $FAST; then
  if $VERBOSE; then echo "Sending API request with fast strategy"; fi
  STRATEGY="-fast"
  JSON_OUTPUT_FILEPATH=${TMP_OUTPUTS_DIR}/${FILENAME}${STRATEGY}.json
  CURL_STRATEGY=(-F "strategy=fast")
elif $OCR_ONLY; then
  STRATEGY="-ocr-only"
  JSON_OUTPUT_FILEPATH=${TMP_OUTPUTS_DIR}/${FILENAME}${STRATEGY}.json
  CURL_STRATEGY=(-F "strategy=ocr_only")
else
  if $VERBOSE; then echo "Sending API request WITHOUT a strategy"; fi
  JSON_OUTPUT_FILEPATH=${TMP_OUTPUTS_DIR}/${FILENAME}${STRATEGY}.json
  CURL_STRATEGY=()
fi

CURL_API_KEY=()
[[ -n "$API_KEY" ]] && CURL_API_KEY=(-H "unstructured-api-key: $API_KEY")
CURL_COORDINATES=()
[[ "$COORDINATES" == "true" ]] && CURL_COORDINATES=(-F "coordinates=true")
CURL_TABLES=()
[[ "$TABLES" == "true" ]] && CURL_TABLES=(-F "skip_infer_table_types='[]'")

curl -q -X 'POST' \
  "$API_ENDPOINT" \
  "${CURL_API_KEY[@]}" -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  "${CURL_STRATEGY[@]}" "${CURL_COORDINATES[@]}" "${CURL_TABLES[@]}" -F "files=@${INPUT_FILEPATH}" \
  -o "${JSON_OUTPUT_FILEPATH}"

JSON_FILE_SIZE=$(wc -c <"${JSON_OUTPUT_FILEPATH}")
if [ "$JSON_FILE_SIZE" -lt 10 ]; then
  echo "Error: JSON file ${JSON_OUTPUT_FILEPATH} has no elements."
  cat "$JSON_OUTPUT_FILEPATH"
  exit 1
else
  # shellcheck disable=SC2046
  if $VERBOSE; then
    echo "first 8 elements: "
    jq '.[0:8]' "${JSON_OUTPUT_FILEPATH}"
  fi
  # shellcheck disable=SC2046
  echo "total number of elements: " $(jq 'length' "${JSON_OUTPUT_FILEPATH}")
fi
echo "JSON Output file: ${JSON_OUTPUT_FILEPATH}"

# write .json output to s3 location
if [ -n "$S3" ]; then

  if [ -z "$S3_URI_PREFIX" ]; then
    echo
    echo "You must define your s3 output location in the env var UNST_S3_JSON_OUTPUT_URI"
    echo "e.g. UNST_S3_JSON_OUTPUT_URI='s3://bucket/path/'"
    exit 0
  elif [ -z "$S3_REGION" ]; then
    echo
    echo "You must define your s3 region in the env var UNST_S3_JSON_OUTPUT_REGION"
    echo "e.g. UNST_S3_JSON_OUTPUT_REGION=us-west-2"
    exit 0
  fi

  SHA_SUM_PREFIX=$(sha256sum "${JSON_OUTPUT_FILEPATH}" | cut -c1-7)
  CURRENT_TIMESTAMP=$(date -u +%s)
  APR27_2023_TIMESTAMP=$(date -u -d "2023-04-27 00:00:00" +%s)
  TENS_OF_SECS_SINCE_APR27_2023=$(((CURRENT_TIMESTAMP - APR27_2023_TIMESTAMP) / 10))

  S3_UPLOAD_PATH="${S3_URI_PREFIX}${TENS_OF_SECS_SINCE_APR27_2023}-${SHA_SUM_PREFIX}${STRATEGY}/${FILENAME}.json"
  if $VERBOSE; then echo "Uploading JSON to S3"; fi
  aws s3 cp "${JSON_OUTPUT_FILEPATH}" "$S3_UPLOAD_PATH"

  BUCKET=$(echo "$S3_UPLOAD_PATH" | cut -d/ -f3)
  KEY=$(echo "$S3_UPLOAD_PATH" | cut -d/ -f4-)
  HTTPS_URL="https://${BUCKET}.s3.us-east-2.amazonaws.com/${KEY}"

  echo "s3 location: ${S3_UPLOAD_PATH}"
  echo "link: $HTTPS_URL"
  copy_to_clipboard "$HTTPS_URL"
else
  copy_to_clipboard "${JSON_OUTPUT_FILEPATH}"
fi
