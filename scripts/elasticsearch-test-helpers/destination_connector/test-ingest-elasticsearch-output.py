#!/usr/bin/env python3

import sys

from elasticsearch import Elasticsearch
from es_cluster_config import (
    CLUSTER_URL,
    INDEX_NAME,
)

N_ELEMENTS = 11933

if __name__ == "__main__":
    print(f"Checking contents of index" f"{INDEX_NAME} at {CLUSTER_URL}")

    print("Connecting to the Elasticsearch cluster.")
    client = Elasticsearch(CLUSTER_URL, request_timeout=30)
    print(client.info())

    # es.indices.refresh(index=INDEX_NAME)
    count = int(client.cat.count(index=INDEX_NAME, format="json")[0]["count"])
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(
            "Elasticsearch dest check failed:"
            f"got {count} items in index, expected {N_ELEMENTS} items in index."
        )
    print("Elasticsearch destination test was successful")
