#!/usr/bin/env python3

import sys

from opensearchpy import OpenSearch

N_ELEMENTS = 5
EXPECTED_TEXT = "To Whom it May Concern:"

if __name__ == "__main__":
    print("Connecting to the OpenSearch cluster.")
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_auth=("admin", "admin"),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )
    print(client.info())

    initial_query = {"query": {"simple_query_string": {"fields": ["text"], "query": EXPECTED_TEXT}}}
    initial_result = client.search(index="ingest-test-destination", body=initial_query)
    initial_embeddings = initial_result["hits"]["hits"][0]["_source"]["embeddings"]

    query = {"size": 1, "query": {"knn": {"embeddings": {"vector": initial_embeddings, "k": 1}}}}

    vector_search = client.search(index="ingest-test-destination", body=query)

    try:
        assert vector_search["hits"]["hits"][0]["_source"]["text"] == EXPECTED_TEXT
        print("OpenSearch vector search test was successful.")
    except AssertionError:
        sys.exit(
            "OpenSearch dest check failed:" f"Did not find {EXPECTED_TEXT} in via vector search."
        )

    count = int(client.count(index="ingest-test-destination")["count"])
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(
            "OpenSearch dest check failed:"
            f"got {count} items in index, expected {N_ELEMENTS} items in index."
        )
    print(f"OpenSearch destination test was successful with {count} items being uploaded.")
