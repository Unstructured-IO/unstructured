#!/usr/bin/env bash

set -euo pipefail

cleanup() {
  rm -rf unstructured-api
}

handle_error() {
  cleanup
  exit 1
}

# Remove the unstructured-api directory if it exists
if [ -d "unstructured-api" ]; then
  rm -rf unstructured-api
fi

# Clone the repository
git clone https://github.com/Unstructured-IO/unstructured-api.git --depth 1

# Install dependencies and project locally
cd unstructured-api && make install && cd ../
make install-project-local
pip show unstructured | grep Version

# Run tests and capture exit status
(cd unstructured-api && make test)
test_exit_status=$?

# Check the exit status and handle errors
if [ $test_exit_status -ne 0 ]; then
  echo "Test failed, see the error message above."
  handle_error
fi

cleanup

echo "Test and cleanup completed successfully."
