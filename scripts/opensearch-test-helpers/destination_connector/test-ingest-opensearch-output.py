#!/usr/bin/env python3

import sys

from opensearchpy import OpenSearch

# from es_cluster_config import (
#     CLUSTER_URL,
#     INDEX_NAME,
#     PASSWORD,
#     USER,
# )

N_ELEMENTS = 1404

if __name__ == "__main__":
    # print(f"Checking contents of index" f"{INDEX_NAME} at {CLUSTER_URL}")

    print("Connecting to the OpenSearch cluster.")
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_auth=("admin", "admin"),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )
    print(client.info())

    count = int(client.count(index="ingest-test-destination")["count"])
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(
            "OpenSearch dest check failed:"
            f"got {count} items in index, expected {N_ELEMENTS} items in index."
        )
    print(f"OpenSearch destination test was successful with {count} items being uploaded.")
