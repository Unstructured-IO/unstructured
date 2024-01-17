#!/usr/bin/env python3

from opensearch_cluster_config import (
    INDEX_NAME,
    mappings,
)
from opensearchpy import OpenSearch

print("Connecting to the OpenSearch cluster.")
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "admin"),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
)
print(client.info())

print("Creating an OpenSearch index for testing ingest opensearch destination connector.")
response = client.indices.create(index=INDEX_NAME, body=mappings)
if not response["acknowledged"]:
    raise RuntimeError("failed to create index")

print("Succesfully created an OpenSearch index for testing opensearch ingest.")
