#!/usr/bin/env python3

from elasticsearch import Elasticsearch
from es_cluster_config import (
    CLUSTER_URL,
    INDEX_NAME,
    PASSWORD,
    USER,
    mappings,
)

print("Connecting to the Elasticsearch cluster.")
es = Elasticsearch(CLUSTER_URL, basic_auth=(USER, PASSWORD), request_timeout=30)
print(f"{es.info()}")

print("Creating an Elasticsearch index for testing ingest elasticsearch destination connector.")
response = es.options(max_retries=5).indices.create(index=INDEX_NAME, mappings=mappings)
if response.meta.status != 200:
    raise RuntimeError("failed to create index")

es.indices.refresh(index=INDEX_NAME)
response = es.cat.count(index=INDEX_NAME, format="json")

print("Succesfully created an Elasticsearch index for testing elasticsearch ingest.")
