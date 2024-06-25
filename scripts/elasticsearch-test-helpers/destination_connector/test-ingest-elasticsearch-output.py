#!/usr/bin/env python3

from time import sleep, time
from typing import List

import click
from elasticsearch import Elasticsearch
from es_cluster_config import (
    CLUSTER_URL,
    INDEX_NAME,
    PASSWORD,
    USER,
)

from unstructured.embed.huggingface import HuggingFaceEmbeddingConfig, HuggingFaceEmbeddingEncoder


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


def validate_count(client: Elasticsearch, num_elements: int):
    print(f"Validating that the count of documents in index {INDEX_NAME} is {num_elements}")
    count = int(client.cat.count(index=INDEX_NAME, format="json")[0]["count"])
    consistent = False
    consistent_count = 1
    desired_consistent_count = 5
    timeout = 60
    sleep_interval = 1
    start_time = time()
    print(f"initial count returned: {count}")
    while not consistent and time() - start_time < timeout:
        new_count = int(client.cat.count(index=INDEX_NAME, format="json")[0]["count"])
        print(f"latest count returned: {new_count}")
        if new_count == count:
            consistent_count += 1
        else:
            count = new_count
            consistent_count = 1
        sleep(sleep_interval)
        if consistent_count >= desired_consistent_count:
            consistent = True
    if not consistent:
        raise TimeoutError(f"failed to get consistent count after {timeout}s")
    assert count == num_elements, (
        f"Elasticsearch dest check failed: got {count} items in index, "
        f"expected {num_elements} items in index."
    )
    print(f"Elasticsearch destination test was successful with {count} items being uploaded.")


def get_embeddings_len(client: Elasticsearch) -> int:
    res = client.search(index=INDEX_NAME, size=1, query={"match_all": {}})
    return len(res["hits"]["hits"][0]["_source"]["embeddings"])


def validate_embeddings(client: Elasticsearch, embeddings: list[float]):
    # Query the index using the appropriate embedding vector for given query text
    # Verify that the top 1 result matches the expected chunk by checking the start text
    print("Testing query to the embedded index.")
    es_embeddings_len = get_embeddings_len(client=client)
    assert len(embeddings) == es_embeddings_len, (
        f"length of embeddings ({len(embeddings)}) doesn't "
        f"match what exists in Elasticsearch ({es_embeddings_len})"
    )
    query_string = {
        "field": "embeddings",
        "query_vector": embeddings,
        "k": 10,
        "num_candidates": 10,
    }
    query_response = client.search(index=INDEX_NAME, knn=query_string)
    response_found = query_response["hits"]["hits"][0]["_source"]
    assert response_found["embeddings"] == embeddings
    print("Query to the embedded index was successful and returned the expected result.")


def validate(num_elements: int, embeddings: list[float]):
    print(f"Checking contents of index" f"{INDEX_NAME} at {CLUSTER_URL}")

    print("Connecting to the Elasticsearch cluster.")
    client = Elasticsearch(CLUSTER_URL, basic_auth=(USER, PASSWORD), request_timeout=30)
    print(client.info())
    validate_count(client=client, num_elements=num_elements)
    validate_embeddings(client=client, embeddings=embeddings)


def parse_embeddings(embeddings_str: str) -> list[float]:
    if embeddings_str.startswith("["):
        embeddings_str = embeddings_str[1:]
    if embeddings_str.endswith("]"):
        embeddings_str = embeddings_str[:-1]
    embeddings_split = embeddings_str.split(",")
    embeddings_split = [e.strip() for e in embeddings_split]
    return [float(e) for e in embeddings_split]


@click.command()
@click.option(
    "--num-elements", type=int, required=True, help="The expected number of elements to exist"
)
@click.option("--embeddings", type=str, required=True, help="List of embeddings to test")
def run_validation(num_elements: int, embeddings: str):
    try:
        parsed_embeddings = parse_embeddings(embeddings_str=embeddings)
    except ValueError as e:
        raise TypeError(
            f"failed to parse embeddings string into list of float: {embeddings}"
        ) from e
    validate(num_elements=num_elements, embeddings=parsed_embeddings)


if __name__ == "__main__":
    run_validation()
