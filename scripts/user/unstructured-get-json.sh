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
  --freemium      Use the free API rather paid API
  --hi-res        hi_res strategy: Enable high-resolution processing, with layout segmentation and OCR
  --fast          fast strategy: No OCR, just extract embedded text
  --ocr-only      ocr_only strategy: Perform OCR (Optical Character Recognition) only. No layout segmentation.
  --vlm           vlm strategy: Use Vision Language Model for processing
  --vlm-provider  Specify the VLM model provider
                  (see: https://docs.unstructured.io/api-reference/workflow/workflows#vlm-strategy)
  --vlm-model     Specify the VLM model when using
                  (see: https://docs.unstructured.io/api-reference/workflow/workflows#vlm-strategy)
  --tables        Enable table extraction: tables are represented as html in metadata
  --images        Include base64images in json
  --coordinates   Include coordinates in the output
  --trace         Enable trace logging for debugging, useful to cut and paste the executed curl call
  --verbose       Enable verbose logging including printing first 8 elements to stdout
  --s3            Write the resulting output to s3 (like a pastebin)
  --write-html    Convert JSON output to HTML. Set the env var $UNST_WRITE_HTML to skip providing this option.
  --open-html     Automatically open HTML output in browser (macOS only) if --write-html. 
                  Set the env var UNST_AUTO_OPEN_HTML=true to skip providing this option.
  --help          Display this help and exit.


Arguments:
  <file>          File to send to the API.

If running against an API instance other than hosted Unstructured paid API (or --freemium),
set the enviornment variable UNST_API_ENDPOINT.

The script requires a <file>, the document to post to the Unstructured API.
The .json result is written to ~/tmp/unst-outputs/ -- this path is echoed and copied to your clipboard.
'

if [ "$#" -eq 0 ]; then
  echo "$USAGE_MESSAGE"
  exit 1
fi

IMAGE_BLOCK_TYPES=${IMAGE_BLOCK_TYPES:-'"image", "table"'}
API_KEY=${UNST_API_KEY:-""}
TMP_DOWNLOADS_DIR=${UNST_SCRIPT_DOWNLOADS_DIR:-"$HOME/tmp/unst-downloads"}
TMP_OUTPUTS_DIR=${UNST_SCRIPT_JSON_OUTPUTS_DIR:-"$HOME/tmp/unst-outputs"}
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
VLM=false
STRATEGY=""
VERBOSE=false
TRACE=false
COORDINATES=false
FREEMIUM=false
TABLES=true
IMAGES=false
S3=""
WRITE_HTML=${UNST_WRITE_HTML:-false}
OPEN_HTML=${UNST_AUTO_OPEN_HTML:-false}
VLM_PROVIDER=""
VLM_MODEL=""

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
  --vlm)
    VLM=true
    shift
    ;;
  --vlm-provider)
    if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
      VLM_PROVIDER=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
    ;;
  --vlm-model)
    if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
      VLM_MODEL=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
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
  --write-html)
    WRITE_HTML=true
    shift
    ;;
  --open-html)
    OPEN_HTML=true
    shift
    ;;
  --tables)
    TABLES=true
    shift
    ;;
  --images)
    IMAGES=true
    shift
    ;;
  --coordinates)
    COORDINATES=true
    shift
    ;;
  --freemium)
    FREEMIUM=true
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

# Check for strategy conflicts after all arguments are processed
STRATEGY_COUNT=0
$HI_RES && STRATEGY_COUNT=$((STRATEGY_COUNT + 1))
$FAST && STRATEGY_COUNT=$((STRATEGY_COUNT + 1))
$OCR_ONLY && STRATEGY_COUNT=$((STRATEGY_COUNT + 1))
$VLM && STRATEGY_COUNT=$((STRATEGY_COUNT + 1))

if [ "$STRATEGY_COUNT" -gt 1 ]; then
  echo "Error: Only one strategy option (--hi-res, --fast, --ocr-only, --vlm) can be specified at a time."
  exit 1
fi

# Check if vlm-provider or vlm-model are provided without --vlm
if { [ -n "$VLM_PROVIDER" ] || [ -n "$VLM_MODEL" ]; } && ! $VLM; then
  echo "Error: --vlm-provider or --vlm-model can only be used with --vlm strategy."
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

if $FREEMIUM; then
  API_ENDPOINT="https://api.unstructured.io/general/v0/general"
else
  API_ENDPOINT=${UNST_API_ENDPOINT:-"https://api.unstructuredapp.io/general/v0/general"}
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
elif $VLM; then
  if $VERBOSE; then echo "Sending API request with vlm strategy"; fi
  STRATEGY="-vlm"
  # Add provider and model to filename if specified
  if [ -n "$VLM_PROVIDER" ] && [ -n "$VLM_MODEL" ]; then
    STRATEGY="-vlm-${VLM_PROVIDER}-${VLM_MODEL}"
  elif [ -n "$VLM_PROVIDER" ]; then
    STRATEGY="-vlm-${VLM_PROVIDER}"
  elif [ -n "$VLM_MODEL" ]; then
    STRATEGY="-vlm-model-${VLM_MODEL}"
  fi
  JSON_OUTPUT_FILEPATH=${TMP_OUTPUTS_DIR}/${FILENAME}${STRATEGY}.json
  CURL_STRATEGY=(-F "strategy=vlm")
  if [ -n "$VLM_PROVIDER" ]; then
    CURL_STRATEGY+=(-F "vlm_model_provider=$VLM_PROVIDER")
  fi
  if [ -n "$VLM_MODEL" ]; then
    CURL_STRATEGY+=(-F "vlm_model=$VLM_MODEL")
  fi
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
CURL_IMAGES=()
[[ "$IMAGES" == "true" ]] && CURL_IMAGES=(-F "extract_image_block_types=[$IMAGE_BLOCK_TYPES]")

curl -q -X 'POST' \
  "$API_ENDPOINT" \
  "${CURL_API_KEY[@]}" -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  "${CURL_STRATEGY[@]}" "${CURL_COORDINATES[@]}" "${CURL_TABLES[@]}" "${CURL_IMAGES[@]}" -F "files=@${INPUT_FILEPATH}" \
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

# Convert JSON to HTML if requested
if [ "$WRITE_HTML" = true ]; then
  HTML_OUTPUT_FILEPATH=${JSON_OUTPUT_FILEPATH%.json}.html

  if $VLM; then
    # VLM output has all metadata.text_as_html fields defined, so
    # create HTML directly from the metadata.text_as_html fields
    {
      echo "<!DOCTYPE html>"
      echo "<html>"
      echo "<head>"
      echo "  <meta charset=\"UTF-8\">"
      echo "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
      echo "  <title>${FILENAME}</title>"
      echo "  <style>"
      echo "    body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }"
      echo "  </style>"
      echo "</head>"
      echo "<body>"
      jq -r 'map(.metadata.text_as_html) | join("\n")' "${JSON_OUTPUT_FILEPATH}"
      echo "</body>"
      echo "</html>"
    } >"${HTML_OUTPUT_FILEPATH}"
    echo "HTML written directly from metadata.text_as_html fields to: ${HTML_OUTPUT_FILEPATH}"
  else
    # most elements will not have metadata.text_as_html defined (by design on Table elements do),
    # so use the unstructured library's python script for the conversion.
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PYTHONPATH="${SCRIPT_DIR}/../.." python3 "${SCRIPT_DIR}/../convert/elements_json_to_format.py" "${JSON_OUTPUT_FILEPATH}" --outdir "${TMP_OUTPUTS_DIR}"
    echo "HTML written using Python script to: ${HTML_OUTPUT_FILEPATH}"
  fi

  # Open HTML file in browser if requested and on macOS
  if [ "$OPEN_HTML" = true ] && [ "$(uname)" == "Darwin" ]; then
    open "${HTML_OUTPUT_FILEPATH}"
  fi
fi

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
