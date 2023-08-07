#!/usr/bin/env bash

# Processes all the documents in all bases (and all workspaces) within an Airtable org,
# using the `unstructured` library.

# Structured outputs are stored in airtable-ingest-output
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/../../.. || exit 1

# Obtain your personal access token, save/source them from another file, for security reasons:
# source "./../../secrets/airtable.txt"
# ...
# --airtable-personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN"

# Other arguments that you can use:
# --list-of-paths
#     --> A list of paths that specify the set of specific locations to ingest data from.
#     --list-of-paths: path1 path2 path3 ….
#     path: base_id/table_id(optional)/view_id(optional)/

#     Here is an example for one --airtable-list-of-paths:
#         base1/		→ gets the entirety of all tables inside workspace7/base1
#         base1/table1		→ gets all rows and columns within described table
#         base1/table1/view1	→ gets the rows and columns that are visible in view1

#     Examples to invalid paths:
#         table1                        → has to mention base to be valid
#         base1/view1			→ has to mention table to be valid

PYTHONPATH=. ./unstructured/ingest/main.py \
        airtable \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
        --structured-output-dir airtable-ingest-output \
        --num-processes 2 \
        --reprocess
