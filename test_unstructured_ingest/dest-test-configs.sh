#!/usr/bin/env bash
core_tests=(
  'azure.sh'
  'gcs.sh'
  's3.sh'
)
tests_to_ignore=(
  'notion.sh'
  'dropbox.sh'
  'sharepoint.sh'
)
all_eval=()