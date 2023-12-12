#!/usr/bin/env bash
# shellcheck disable=SC2034

core_tests=(
	'sharepoint.sh'
	'local.sh'
	'local-single-file.sh'
	'local-single-file-with-encoding.sh'
	'local-single-file-with-pdf-infer-table-structure.sh'
	's3.sh'
	'google-drive.sh'
	'gcs.sh'
	'azure.sh'
)
tests_to_ignore=(
	'notion.sh'
	'dropbox.sh'
)
tests_to_omit=(
	'airtable-large.sh'
	'pdf-fast-reprocess.sh'
)
all_eval=(
	'text-extraction'
	'element-type'
)
