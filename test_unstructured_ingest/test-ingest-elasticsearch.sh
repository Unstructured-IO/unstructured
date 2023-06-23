#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

# Create the elasticsearch cluster and get the container id
output=$(docker run -d --rm -p 9200:9200 -p 9300:9300 -e "xpack.security.enabled=false" -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.7.0)
container_id=$(echo $output | cut -c 1-12)
echo $container

url="http://localhost:9200/_cluster/health"
status_code=0
retry_count=0
max_retries=6

# Check the cluster status repeatedly until it becomes live or maximum retries are reached
while [ "$status_code" -ne 200 ] && [ "$retry_count" -lt "$max_retries" ]; do

  # Send a GET request to the cluster health API
  response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  status_code="$response"

  # Process the files only when the ES cluster is live
  if [ "$status_code" -eq 200 ]; then
    echo "Cluster is live."

    python examples/ingest/elasticsearch/elasticsearch_cluster.py

    PYTHONPATH=. ./unstructured/ingest/main.py \
            --elasticsearch-url http://localhost:9200 \
            --elasticsearch-index-name movies \
            --jq-query '{ethnicity, director}' \
            --structured-output-dir elasticsearch-ingest-output \
            --num-processes 2

  else
    ((retry_count++))
    echo "Cluster is not available. Retrying in 5 seconds... (Attempt $retry_count)"
    sleep 5
  fi
done

# If cluster has not got live, exit after a certain number of tries
if [ "$status_code" -ne 200 ]; then
  echo "Cluster took an unusually long time to create (>25 seconds). Expected time is around 10 seconds. Exiting."
fi

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

# Kill the container so the script can be repeatedly run using the same ports
"docker stop '$container_id'" ERR

# # Kill even when there's an error from the previous commands
trap "docker stop '$container_id'" ERR

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp elasticsearch-ingest-output/* test_unstructured_ingest/expected-structured-output/elasticsearch-ingest-output/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/elasticsearch-ingest-output elasticsearch-ingest-output ; then
    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
    echo
    echo "  export OVERWRITE_FIXTURES=true"
    echo
    echo "and then rerun this script."
    echo
    echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
    echo "to update fixtures for CI."
    echo
    exit 1

fi
