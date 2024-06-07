#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-kafka-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
writer_processes=$(((max_processes - 1) > 1 ? (max_processes - 1) : 2))

if [ -z "$KAFKA_API_KEY" ]; then
	echo "Skipping Kafka ingest test because KAFKA_API_KEY env var is not set."
	exit 0
fi

if [ -z "$KAFKA_SECRET" ]; then
	echo "Skipping Kafka ingest test because KAFKA_SECRET env var is not set."
	exit 0
fi

if [ -z "$KAFKA_BOOTSTRAP_SERVER" ]; then
	echo "Skipping Kafka ingest test because KAFKA_BOOTSTRAP_SERVER env var is not set."
	exit 0
fi


if [ -z "$KAFKA_CLUSTER_ID" ]; then
	echo "Skipping Kafka ingest test because KAFKA_CLUSTER_ID env var is not set."
	exit 0
fi

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

LC_ALL=C

# Set the variables with default values if they're not set in the environment
KAFKA_TOPIC=${KAFKA_TOPIC:-"ingest-test-$RANDOM_SUFFIX"}

# Combine the API key and secret
API_KEY_SECRET="$KAFKA_API_KEY:$KAFKA_SECRET"
# Base64 encode the combined string
ENCODED_CREDENTIALS=$(echo $API_KEY_SECRET | base64)
# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
	# Local file cleanupcd .
	cleanup_dir "$WORK_DIR"
	cleanup_dir "$OUTPUT_DIR"

	echo "Deleting topic $KAFKA_TOPIC"

	response_code=$(curl \
	-s -o /dev/null \
	-w "%{http_code}" \
	--request DELETE \
	--url "https://$KAFKA_BOOTSTRAP_SERVER:443/kafka/v3/clusters/$KAFKA_CLUSTER_ID/topics/$KAFKA_TOPIC" \
	--header "Authorization: Basic $ENCODED_CREDENTIALS" \
	--header "Content-Type: application/json" 
	)
	echo "Topic deletion response HTTP status code: $response_code"
}

trap cleanup EXIT 
echo "Creating topic $KAFKA_TOPIC"
response_code=$(curl \
	-s -o /dev/null \
	-w "%{http_code}" \
	--request POST \
	--url "https://$KAFKA_BOOTSTRAP_SERVER:443/kafka/v3/clusters/$KAFKA_CLUSTER_ID/topics" \
	--header "Authorization: Basic $ENCODED_CREDENTIALS" \
	--header "Content-Type: application/json" \
	--data '
{
	"topic_name":"'"$KAFKA_TOPIC"'",
    "partitions_count": 1,
    "replication_factor": 3
}
')

if [ "$response_code" -lt 400 ]; then
	echo "Index creation success: $response_code"
else
	echo "Index creation failure: $response_code"
	exit 1
fi

#unstructured/ingest/main.py local --input-path=test_unstructured_ingest/example-docs/layout-parser-paper.pdf kafka 
#--bootstrap-server=pkc-921jm.us-east-2.aws.confluent.cloud --port 9092 --topic unstructured  
#--kafka-api-key=V57DL5J624GLFGLY --secret=c1I566vbopRLqU/5SIj5BT8/KWFPQh6gW9Kxu78zGlUhQTayt3uCcMva08QFQ5/S 
#--num-processes=1

PYTHONPATH=. ./unstructured/ingest/main.py \
	local \
	--num-processes "$max_processes" \
	--output-dir "$OUTPUT_DIR" \
	--strategy fast \
	--verbose \
	--reprocess \
	--input-path example-docs/layout-parser-paper.pdf \
	--work-dir "$WORK_DIR" \
	--chunk-elements \
	--chunk-combine-text-under-n-chars 200 --chunk-new-after-n-chars 2500 --chunk-max-characters 38000 --chunk-multipage-sections \
	--embedding-provider "langchain-huggingface" \
	kafka \
	--kafka-api-key "$KAFKA_API_KEY" \
	--secret "$KAFKA_SECRET" \
	--topic "$KAFKA_TOPIC" \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--num-processes "$writer_processes" \
	--port 9092

#Check the number of messages in destination topic
python "$SCRIPT_DIR"/python/test-kafka-output.py check \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--topic "$KAFKA_TOPIC" \
	--api-key "$KAFKA_API_KEY" \
	--secret "$KAFKA_SECRET"