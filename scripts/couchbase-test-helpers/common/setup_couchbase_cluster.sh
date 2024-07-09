#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
ENV_FILE="$SCRIPT_DIR"/constants.env

source "$ENV_FILE"

docker compose version
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml up --wait
docker compose -f "$SCRIPT_DIR"/docker-compose.yaml ps

echo "Cluster is live."

echo "Initializing Couchbase cluster"
docker exec -it couchbase-db couchbase-cli cluster-init -c $CB_CONN_STR \
        --cluster-username $CB_USERNAME --cluster-password $CB_PASSWORD --cluster-ramsize 512 \
        --cluster-index-ramsize 512 --services data,index,query,fts \
&& \
docker exec -it couchbase-db couchbase-cli bucket-create -c $CB_CONN_STR \
    --username $CB_USERNAME --password $CB_PASSWORD \
    --bucket $CB_BUCKET --bucket-type couchbase --bucket-ramsize 200

echo "Couchbase cluster initialized"

python "$SCRIPT_DIR"/check_cluster_health.py \
  --username "$CB_USERNAME" \
  --password "$CB_PASSWORD" \
  --connection_string "$CB_CONN_STR" \
  --bucket_name "$CB_BUCKET"
wait