#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../.. || exit 1

id_log_filepath="scripts/elasticsearch-test-helpers/elasticsearch-docker_container_id.txt"

# Create the elasticsearch cluster and get the container id
output=$(docker run -d --rm -p 9200:9200 -p 9300:9300 -e "xpack.security.enabled=false" -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.7.0)
container_id=$(echo "$output" | cut -c 1-12)
echo "$container_id" > "$id_log_filepath"

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

    python scripts/elasticsearch-test-helpers/create_and_fill_es.py

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
