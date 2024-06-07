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

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

LC_ALL=C

# Set the variables with default values if they're not set in the environment
KAFKA_TOPIC=${KAFKA_TOPIC:-"ingest-test-$RANDOM_SUFFIX"}


source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
	# Local file cleanupcd .
	cleanup_dir "$WORK_DIR"
	cleanup_dir "$OUTPUT_DIR"


	echo "Stopping local Kafka instance"
	docker-compose -f scripts/kafka-test-helpers/docker-compose.yml down --remove-orphans -v
}

trap cleanup EXIT 

echo "Creating local Kafka instance"
# shellcheck source=/dev/null
scripts/kafka-test-helpers/create-kafka-instance.sh 
wait

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
	--topic "$KAFKA_TOPIC" \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--num-processes "$writer_processes" \
	--port 29092 \
	--confluent false

echo "Checking for matching messages in Kafka"

#Check the number of messages in destination topic
python "$SCRIPT_DIR"/python/test-kafka-output.py check \
	--bootstrap-server "$KAFKA_BOOTSTRAP_SERVER" \
	--topic "$KAFKA_TOPIC" \
	--confluent false \
	--port 29092