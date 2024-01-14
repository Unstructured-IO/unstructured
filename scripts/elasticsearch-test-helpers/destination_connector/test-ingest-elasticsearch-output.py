#!/usr/bin/env python3

import sys
from typing import List

from elasticsearch import Elasticsearch
from es_cluster_config import (
    CLUSTER_URL,
    INDEX_NAME,
    PASSWORD,
    USER,
)

from unstructured.embed.huggingface import HuggingFaceEmbeddingConfig, HuggingFaceEmbeddingEncoder

N_ELEMENTS = 1404


def embeddings_for_text(text: str) -> List[float]:
    embedding_encoder = HuggingFaceEmbeddingEncoder(config=HuggingFaceEmbeddingConfig())
    return embedding_encoder.embed_query(text)


def query(client: Elasticsearch, search_text: str):
    # Query the index using the appropriate embedding vector for given query text
    search_vector = embeddings_for_text(search_text)
    # Constructing the search query
    query = {
        "query": {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'embeddings') + 1.0",
                    "params": {"query_vector": search_vector},
                },
            }
        }
    }
    return client.search(index=INDEX_NAME, body=query)


if __name__ == "__main__":
    print(f"Checking contents of index" f"{INDEX_NAME} at {CLUSTER_URL}")

    print("Connecting to the Elasticsearch cluster.")
    client = Elasticsearch(CLUSTER_URL, basic_auth=(USER, PASSWORD), request_timeout=30)
    print(client.info())

    count = int(client.cat.count(index=INDEX_NAME, format="json")[0]["count"])
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        sys.exit(
            "Elasticsearch dest check failed:"
            f"got {count} items in index, expected {N_ELEMENTS} items in index."
        )
    print(f"Elasticsearch destination test was successful with {count} items being uploaded.")

    # Query the index using the appropriate embedding vector for given query text
    # Verify that the top 1 result matches the expected chunk by checking the start text
    print("Testing query to the embedded index.")
    query_text = (
        "A gathering of Russian nobility and merchants in historic uniforms, "
        "discussing the Emperor's manifesto with a mix of solemn anticipation "
        "and everyday concerns, while Pierre, dressed in a tight nobleman's uniform, "
        "ponders the French Revolution and social contracts amidst the crowd."
    )
    query_response = query(client, query_text)
    assert query_response["hits"]["hits"][0]["_source"]["text"].startswith("CHAPTER XXII")
    print("Query to the embedded index was successful and returned the expected result.")
