#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=kafka
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$OUTPUT_ROOT/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

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
#DO not change this name, it needs to match expected output file name in ../expected-structured-output/kafka/
KAFKA_TOPIC="fake-topic"
KAFKA_TOPIC=${KAFKA_TOPIC:-"ingest-test-$RANDOM_SUFFIX"}
# Combine the API key and secret
API_KEY_SECRET="$KAFKA_API_KEY:$KAFKA_SECRET"
# Base64 encode the combined string
ENCODED_CREDENTIALS=$(echo $API_KEY_SECRET | base64)

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
# shellcheck disable=SC2317
function cleanup() {
	cleanup_dir "$OUTPUT_DIR"
	cleanup_dir "$WORK_DIR"
	if [ "$CI" == "true" ]; then
		echo "here"
		cleanup_dir "$DOWNLOAD_DIR"
	fi

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
    "replication_factor": 3,
	"configs": [
		{
		"name":"max.message.bytes",
		"value":8330000
	}
	]
}
')

if [ "$response_code" -lt 400 ]; then
	echo "Index creation success: $response_code"
else
	echo "Index creation failure: $response_code"
	exit 1
fi

#Check the number of messages in destination topic
python "$SCRIPT_DIR"/python/test-produce-kafka-message.py up \
	--input-file "example-docs/layout-parser-paper.pdf" \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--topic "$KAFKA_TOPIC" \
	--api-key "$KAFKA_API_KEY" \
	--secret "$KAFKA_SECRET"


RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
	kafka \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--download-dir "$DOWNLOAD_DIR" \
	--kafka-api-key "$KAFKA_API_KEY" \
	--secret "$KAFKA_SECRET" \
	--topic "$KAFKA_TOPIC" \
	--num-messages-to-consume 1 \
	--port 9092 \
	--metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
	--preserve-downloads \
	--reprocess \
	--output-dir "$OUTPUT_DIR" \
	--verbose \
	--work-dir "$WORK_DIR"

set +e
"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ]; then
	echo "The last script run exited with a non-zero exit code: $EXIT_CODE."
	# Handle the error or exit
fi

"$SCRIPT_DIR"/evaluation-ingest-cp.sh "$OUTPUT_DIR" "$OUTPUT_FOLDER_NAME"

exit $EXIT_CODE