#!/usr/bin/env python3

import os

import weaviate

weaviate_host_url = os.getenv("WEAVIATE_HOST_URL", "http://localhost:8080")
class_name = os.getenv("WEAVIATE_CLASS_NAME", "Pdf_elements")

if __name__ == "__main__":
    print(f"Checking contents of class collection " f"{class_name} at {weaviate_host_url}")

    client = weaviate.Client(
        url=weaviate_host_url,
    )

    response = client.query.aggregate(class_name).with_meta_count().do()
    assert response["data"]["Aggregate"][class_name][0]["meta"]["count"] == 605
    print("weaviate dest check complete")
