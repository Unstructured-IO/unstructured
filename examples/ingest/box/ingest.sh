#!/usr/bin/env bash

# Processes several files in a nested folder structure from box://utic-test-ingest-fixtures/
# through Unstructured's library in 2 processes.

# Structured outputs are stored in box-output/

# Setting up your App/Credential to access Box folders/files:
# First of all, this does not work with a free Box account.
# Make sure the App service email is a collaborator for your folder (co-owner or editor)
# Make sure you have the 'write all files' application scope
# Maybe check 'Make api calls as the as-user header'
# REAUTHORIZE app after making any of the above changes

# box-app-config is the path to a json file, available in the App Settings section of your Box App
# More info to set up the app:
# https://developer.box.com/guides/authentication/jwt/jwt-setup/
# and set up the app config.json file here:
# https://developer.box.com/guides/authentication/jwt/with-sdk/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  box \
  --box-app-config "$BOX_APP_CONFIG_PATH" \
  --remote-url box://utic-test-ingest-fixtures \
  --output-dir box-output \
  --num-processes 2 \
  --recursive \
  --verbose
