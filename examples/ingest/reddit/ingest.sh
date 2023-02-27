***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the Unstructured-IO/unstructured repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in reddit-ingest-output/

***REMOVED*** NOTE, this script is not ready-to-run!
***REMOVED*** You must enter a client ID and a client secret before running.
***REMOVED*** You can find out how to get them here:
***REMOVED*** https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example***REMOVED***first-steps
***REMOVED*** It is quite easy and very quick.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --subreddit-name machinelearning \
    --reddit-client-id "<client id here>" \
    --reddit-client-secret "<client secret here>" \
    --reddit-user-agent "Unstructured Ingest Subreddit fetcher by \u\..." \
    --reddit-search-query "Unstructured" \
    --reddit-num-posts 10 \
    --structured-output-dir reddit-ingest-output \
    --num-processes 2 \
    --verbose

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --subreddit-name ...
