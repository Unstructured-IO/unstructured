#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Create the Elasticsearch cluster and get the container id
docker run -d --rm -p 9200:9200 -p 9300:9300 -e "xpack.security.enabled=false" -e "discovery.type=single-node" --name es-test docker.elastic.co/elasticsearch/elasticsearch:8.7.0

# Wait for Elasticsearch container to start
echo "Waiting for Elasticsearch container to start..."
sleep 1

url="http://localhost:9200/_cluster/health"
status_code=0
retry_count=0
max_retries=6

# Check the cluster status repeatedly until it becomes live or maximum retries are reached
while [ "$status_code" -ne 200 ] && [ "$retry_count" -lt "$max_retries" ]; do
  # Send a GET request to the cluster health API
  response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  status_code="$response"

  # Process the files only when the Elasticsearch cluster is live
  if [ "$status_code" -eq 200 ]; then
    echo "Cluster is live."
    python "$SCRIPT_DIR/create_and_fill_es.py"
  else
    ((retry_count++))
    echo "Cluster is not available. Retrying in 5 seconds... (Attempt $retry_count)"
    sleep 5
  fi
done

# If the cluster has not become live, exit after a certain number of tries
if [ "$status_code" -ne 200 ]; then
  echo "Cluster took an unusually long time to create (>25 seconds). Expected time is around 10 seconds. Exiting."
fi
