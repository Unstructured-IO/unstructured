#!/usr/bin/env bash

# Given a single connector name, run all test scripts associated with it

connector=$1

if [ -z "$connector" ]; then
  echo "usage: $0 connector"
  exit 1
fi

echo "Connector being tested: $connector"

relevant_file=$(ls test_unstructured_ingest/test-ingest-"$connector"*.sh)

exit_statuses=()

# Run each command and capture its exit status
for file in "${relevant_file[@]}"; do
  echo "running $file"
  $file
  exit_statuses+=($?)
done

for status in "${exit_statuses[@]}"; do
  echo "$status"
done


# Check for failures
for status in "${exit_statuses[@]}"; do
  if [[ $status -ne 0 ]]; then
    echo "At least one ingest command failed! Scroll up to see which"
    exit 1
  fi
done

echo "No diffs resulted from any ingest commands"
