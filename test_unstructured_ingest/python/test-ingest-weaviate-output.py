#!/usr/bin/env python3

import os
import sys

import weaviate

weaviate_host_url = os.getenv("WEAVIATE_HOST_URL", "http://localhost:8080")
class_name = os.getenv("WEAVIATE_CLASS_NAME", "Elements")
N_ELEMENTS = 5

if __name__ == "__main__":
    print(f"Checking contents of class collection " f"{class_name} at {weaviate_host_url}")

    client = weaviate.Client(
        url=weaviate_host_url,
    )

    response = client.query.aggregate(class_name).with_meta_count().do()
    count = response["data"]["Aggregate"][class_name][0]["meta"]["count"]
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(f"FAIL: weaviate dest check failed: got {count}, expected {N_ELEMENTS}")
    print("SUCCESS: weaviate dest check")
