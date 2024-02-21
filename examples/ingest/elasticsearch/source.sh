#!/usr/bin/env bash

# Runs a docker container to create an elasticsearch cluster,
# fills the ES cluster with data,
# processes all the files in the 'movies' index in the cluster using the `unstructured` library.

# Structured outputs are stored in elasticsearch-ingest-output

# shellcheck source=/dev/null
sh scripts/elasticsearch-test-helpers/source_connector/create-fill-and-check-es.sh
wait

# Kill the container so the script can be repeatedly run using the same ports
trap 'echo "Stopping Elasticsearch Docker container"; docker stop es-test' EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
  elasticsearch \
  --hosts "<List of URLs where elasticsearch index is served>" \
  --index-name "<Index name to ingest data from>" \
  --username "<Username to authenticate into the index>" \
  --password "<Password to authenticate into the index>" \
  --fields "<If provided, will limit the fields returned by Elasticsearch to this comma-delimited list" \
  --batch-size "<How many records to read at a time per process>" \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --cloud-id "<Id used to connect to Elastic Cloud>" \
  --es-api-key "<Api key used for authentication>" \
  --api-key-id "<Id associated with api key used for authentication: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html>" \
  --bearer-auth "<Bearer token used for HTTP bearer authentication>" \
  --ca-certs "<path/to/ca/certs>" \
  --ssl-assert-fingerprint "<SHA256 fingerprint value>"
