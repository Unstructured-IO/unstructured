#!/usr/bin/env python3

import click
from pymilvus import MilvusClient


def validate_embeddings(client: MilvusClient, collection_name: str, embeddings: list[float]):
    print(f"Checking for perfect match to given embeddings in collection {collection_name}")
    resp = client.search(
        collection_name=collection_name, data=[embeddings], limit=1, output_fields=["embeddings"]
    )
    resp_data = resp[0]
    assert len(resp_data) == 1, f"client response not length 1 ({len(resp_data)}: {resp_data}"
    resp_item = resp_data[0]
    expected_distance = 1.0
    distance = resp_item["distance"]
    dist_diff = abs(distance - expected_distance)
    tolerance = 1e-3
    assert dist_diff < tolerance, (
        f"Difference between expected distance ({expected_distance}) "
        f"and distance returned ({distance}) exceeds tolerance of {tolerance}: {dist_diff}"
    )
    resp_embeddings = resp_item["entity"]["embeddings"]
    assert resp_embeddings == embeddings

    print("embedding validation success")


def validate_count(client: MilvusClient, collection_name: str, expected_count: int):
    print(f"Checking for item count in collection to match {expected_count}")

    count_key = "count(*)"
    resp = client.query(collection_name=collection_name, output_fields=[count_key])
    assert len(resp) == 1, f"client response not length 1 ({len(resp)}: {resp}"
    resp_data = resp[0]
    assert count_key in resp_data, f"count key {count_key} not in response: {resp_data}"
    count = resp_data[count_key]
    assert count == expected_count, f"client response not {expected_count}): {count}"
    print("count validation success")


def validate(
    client: MilvusClient, collection_name: str, embeddings: list[float], expected_count: int
):
    validate_count(client=client, collection_name=collection_name, expected_count=expected_count)
    validate_embeddings(client=client, collection_name=collection_name, embeddings=embeddings)
    print("All validations success")


def parse_embeddings(embeddings_str: str) -> list[float]:
    dropped_characters = ["\n", "\r", " "]
    for dropped_character in dropped_characters:
        embeddings_str = embeddings_str.replace(dropped_character, "")
    if embeddings_str.startswith("["):
        embeddings_str = embeddings_str[1:]
    if embeddings_str.endswith("]"):
        embeddings_str = embeddings_str[:-1]
    embeddings_split = embeddings_str.split(",")
    embeddings_split = [e.strip() for e in embeddings_split]
    return [float(e) for e in embeddings_split]


@click.command("milvus-init")
@click.option("--host", type=str, default="localhost")
@click.option("--port", type=int, default=19530)
@click.option("--db-name", type=str, default="milvus")
@click.option("--collection-name", type=str, default="ingest_test")
@click.option("--embeddings", type=str, required=True, help="List of embeddings to test")
@click.option(
    "--count",
    type=click.IntRange(min=1),
    required=True,
    help="Number of items to expect in collection",
)
def run_validation(
    host: str, port: int, db_name: str, collection_name: str, embeddings: str, count: int
):
    uri = f"http://{host}:{port}"

    print(f"validating outputs in milvus database {db_name} at {uri}")
    try:
        parsed_embeddings = parse_embeddings(embeddings_str=embeddings)
    except ValueError as e:
        raise TypeError(
            f"failed to parse embeddings string into list of float: {embeddings}"
        ) from e
    client = MilvusClient(uri=uri)
    client.using_database(db_name=db_name)
    validate(
        client=client,
        collection_name=collection_name,
        embeddings=parsed_embeddings,
        expected_count=count,
    )


if __name__ == "__main__":
    run_validation()
