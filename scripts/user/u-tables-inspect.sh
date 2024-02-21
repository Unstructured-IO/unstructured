#!/usr/bin/env bash

# TODO:
# * include the page number in output html filename, maybe all tables per page
#   in one html page.

set -e

USAGE_MESSAGE="Usage: $0 <file>

Requires an unstructured output .json file as the only argument.

Each table in the file is saved as an individual html file and
opened in Safari (if running on mac), providing a quick and easy
way to see the structure and content of each Table element.
"

# Check for the presence of an argument
if [ "$#" -ne 1 ]; then
  echo "$USAGE_MESSAGE"
  exit 1
fi

# The JSON file to be processed is the first argument
JSON_FILE="$1"

# Extract the basename without the extension
BASE_NAME=$(basename "$JSON_FILE" .json)

# Directory where the files will be saved
TMP_TABLES_OUTPUTS_DIR="$HOME/tmp/tables-out"

# Check if the directory exists, if not create it
if [ ! -d "$TMP_TABLES_OUTPUTS_DIR" ]; then
  mkdir -p "$TMP_TABLES_OUTPUTS_DIR"
fi

# Counter for the table files
COUNTER=1

# Parsing the JSON and creating HTML files
jq -c '.[] | select(.type == "Table") | .metadata.text_as_html' "$JSON_FILE" | while read -r HTML_CONTENT; do
  # Remove leading and trailing quotes from the JSON string
  HTML_CONTENT=${HTML_CONTENT#\"}
  HTML_CONTENT=${HTML_CONTENT%\"}
  # add a border and padding to clearly see cell definition
  # shellcheck disable=SC2001
  HTML_CONTENT=$(echo "$HTML_CONTENT" | sed 's/<table>/<table border="1" cellpadding="10">/')
  # add newlines for readability in the html
  # shellcheck disable=SC2001
  HTML_CONTENT=$(echo "$HTML_CONTENT" | sed 's/>\s*</>\n</g')

  # Create filename based on the basename and counter
  HTML_FILENAME="$TMP_TABLES_OUTPUTS_DIR/${BASE_NAME}-${COUNTER}.html"

  # Increment the counter
  COUNTER=$((COUNTER + 1))

  # Save the HTML content to a file
  echo "$HTML_CONTENT" >"$HTML_FILENAME"

  if [ "$(uname)" == "Darwin" ]; then
    # Open the file in a new browser window
    open -a "Safari" "$HTML_FILENAME" &
  else
    echo "$HTML_FILENAME"
  fi
done
