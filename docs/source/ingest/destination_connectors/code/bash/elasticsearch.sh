#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
	local \
	--input-path example-docs/book-war-and-peace-1225p.txt \
	--output-dir local-output-to-elasticsearch \
	--strategy fast \
	--chunk-elements \
	--embedding-provider "$EMBEDDING_PROVIDER" \
	--num-processes 2 \
	--verbose \
	elasticsearch \
	--hosts "$ELASTICSEARCH_HOSTS" \
	--username "$ELASTICSEARCH_USERNAME" \
	--password "$ELASTICSEARCH_PASSWORD" \
    --index-name "$ELASTICSEARCH_INDEX_NAME"
