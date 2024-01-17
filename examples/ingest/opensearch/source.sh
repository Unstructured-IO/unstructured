#!/usr/bin/env bash

# Runs a docker container to create an opensearch cluster,
# fills the ES cluster with data,
# processes all the files in the 'movies' index in the cluster using the `unstructured` library.

# Structured outputs are stored in opensearch-ingest-output

# shellcheck source=/dev/null
sh scripts/opensearch-test-helpers/source_connector/create-fill-and-check-opensearch.sh
wait

# Kill the container so the script can be repeatedly run using the same ports
trap 'echo "Stopping opensearch Docker container"; docker stop os-test' EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
  opensearch \
  --hosts "<List of URLs where opensearch index is served>" \
  --index-name "<Index name to ingest data from>" \
  --username "<Username to authenticate into the index>" \
  --password "<Password to authenticate into the index>" \
  --fields "<If provided, will limit the fields returned by opensearch to this comma-delimited list" \
  --batch-size "<How many records to read at a time per process>" \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --ca-certs "<path/to/ca/certs>" \
  --client-cert "<path/to/client/cert>" \
  --client-key "<path/to/client/key>" \
  --use-ssl \
  --verify-certs \
  --ssl-show-warn
