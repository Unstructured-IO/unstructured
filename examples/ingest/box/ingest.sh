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

# box-app-cred is a json file from the App Settings section of your Box App
# More info here:
# https://developer.box.com/guides/authentication/jwt/jwt-setup/


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
   --box-app-cred "$BOX_APP_CRED" \
   --remote-url box://utic-test-ingest-fixtures \
   --structured-output-dir box-output \
   --num-processes 2 \
   --recursive \
   --verbose 