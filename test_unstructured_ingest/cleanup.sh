#!/usr/bin/env bash


function cleanup_dir() {
  local dir_to_cleanup="${1}"
  echo "--- Running cleanup of $dir_to_cleanup ---"

  if [ -d "$dir_to_cleanup" ]; then
    echo "cleaning up directory: $dir_to_cleanup"
    rm -rf "$dir_to_cleanup"
  else
    echo "$dir_to_cleanup does not exist or is not a directory, skipping deletion"
  fi

  echo "--- Cleanup done ---"
}
