#!/usr/bin/env python3

import sys

from elasticsearch import Elasticsearch
from es_cluster_config import (
    CLUSTER_URL,
    INDEX_NAME,
    PASSWORD,
    USER,
)

N_ELEMENTS = 5
EXPECTED_TEXT = "To Whom it May Concern:"

if __name__ == "__main__":
    print(f"Checking contents of index" f"{INDEX_NAME} at {CLUSTER_URL}")

    print("Connecting to the Elasticsearch cluster.")
    client = Elasticsearch(CLUSTER_URL, basic_auth=(USER, PASSWORD), request_timeout=30)
    print(client.info())

    initial_query = {"query": {"simple_query_string": {"fields": ["text"], "query": EXPECTED_TEXT}}}
    initial_result = client.search(index=INDEX_NAME, body=initial_query)
    initial_embeddings = initial_result["hits"]["hits"][0]["_source"]["embeddings"]

    query_string = {
        "field": "embeddings",
        "query_vector": initial_embeddings,
        "k": 1,
        "num_candidates": 100,
    }
    vector_search = client.search(index=INDEX_NAME, knn=query_string)

    try:
        assert vector_search["hits"]["hits"][0]["_source"]["text"] == EXPECTED_TEXT
    except AssertionError:
        sys.exit(
            "Elasticsearch dest check failed:" f"Did not find {EXPECTED_TEXT} in via vector search."
        )

    count = int(client.cat.count(index=INDEX_NAME, format="json")[0]["count"])
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(
            "Elasticsearch dest check failed:"
            f"got {count} items in index, expected {N_ELEMENTS} items in index."
        )
    print(f"Elasticsearch destination test was successful with {count} items being uploaded.")
