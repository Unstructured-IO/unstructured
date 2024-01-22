#!/usr/bin/env bash

# Processes the pdf specified in the input path
# processes the document, and writes to results to a Confluent topic.


SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
	local \
	--input-path="<path to the file to be processed/partitioned>" \
	kafka \
	--bootstrap-server="<bootstrap server fully qualified hostname>" \
	--port "<port, likely 9092>" \
	--topic "<destination topic in confluent>"  \
	--kafka-api-key="<confluent api key>" \
	--secret="<confluent secret>" \
	--num-processes="<number of processes to be used>"
