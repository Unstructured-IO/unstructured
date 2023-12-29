#!/usr/bin/env bash

# Processes all the documents in all bases (in all workspaces) within an Airtable org,
# using the `unstructured` library.

# Structured outputs are stored in airtable-ingest-output
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/../../.. || exit 1

# Required arguments:
# --personal-access-token
#   --> Personal access token to authenticate into Airtable.
#       Check https://support.airtable.com/docs/creating-and-using-api-keys-and-access-tokens for more info.

# Optional arguments that you can use:
# --list-of-paths
#   --> A list of paths that specify the locations to ingest data from within Airtable.
#       If this argument is not set, the connector ingests all tables within each and every base.
#   --list-of-paths: path1 path2 path3 ….
#   path: base_id/table_id(optional)/view_id(optional)/

#     To obtain (base, table, view) ids in bulk, check:
#     https://airtable.com/developers/web/api/list-bases (base ids)
#     https://airtable.com/developers/web/api/get-base-schema (table and view ids)
#     https://pyairtable.readthedocs.io/en/latest/metadata.html (base, table and view ids)

#     To obtain specific ids from Airtable UI, go to your workspace, and copy any
#     relevant id from the URL structure:
#     https://airtable.com/appAbcDeF1ghijKlm/tblABcdEfG1HIJkLm/viwABCDEfg6hijKLM
#     appAbcDeF1ghijKlm -> base_id
#     tblABcdEfG1HIJkLm -> table_id
#     viwABCDEfg6hijKLM -> view_id

#     You can also check: https://support.airtable.com/docs/finding-airtable-ids

#     Here is an example for one --list-of-paths:
#         base1/		→ gets the entirety of all tables inside base1
#         base1/table1		→ gets all rows and columns within table1 in base1
#         base1/table1/view1	→ gets the rows and columns that are visible in view1 for the table1 in base1

#     Examples to invalid paths:
#         table1                        → has to mention base to be valid
#         base1/view1			→ has to mention table to be valid

PYTHONPATH=. ./unstructured/ingest/main.py \
  airtable \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
  --output-dir airtable-ingest-output \
  --num-processes 2 \
  --reprocess
