#!/usr/bin/env python
import json
import time

import click
from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel


def get_client(uri: str) -> MongoClient:
    client = MongoClient(uri)
    client.admin.command("ping")
    print("Successfully connected to MongoDB")
    return client


@click.group(name="mongo-ingest")
@click.option("--uri", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--collection", type=str, required=True)
@click.pass_context
def cli(ctx, uri: str, database: str, collection: str):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    ctx.obj["client"] = get_client(uri)


@cli.command()
@click.pass_context
def up(ctx):
    client = ctx.obj["client"]
    collection_name = ctx.parent.params["collection"]
    db = client[ctx.parent.params["database"]]
    print(f"creating collection {collection_name}")
    collection = db.create_collection(name=collection_name)
    print(f"successfully created collection: {collection_name}")
    if "embeddings" in [c["name"] for c in collection.list_search_indexes()]:
        print("search index already exists, skipping creation")
        return

    search_index_name = collection.create_search_index(
        model=SearchIndexModel(
            name="embeddings",
            definition={
                "mappings": {
                    "dynamic": True,
                    "fields": {
                        "embeddings": [
                            {"type": "knnVector", "dimensions": 384, "similarity": "euclidean"}
                        ]
                    },
                }
            },
        )
    )
    print(f"Added search index: {search_index_name}")


@cli.command()
@click.pass_context
def down(ctx):
    collection_name = ctx.parent.params["collection"]
    client = ctx.obj["client"]
    db = client[ctx.parent.params["database"]]
    if collection_name not in db.list_collection_names():
        print(
            "collection name {} does not exist amongst those in database: {}, "
            "skipping deletion".format(collection_name, ", ".join(db.list_collection_names()))
        )
        return
    print(f"deleting collection: {collection_name}")
    collection = db[collection_name]
    collection.drop()
    print(f"successfully deleted collection: {collection}")


@cli.command()
@click.option("--expected-records", type=int, required=True)
@click.pass_context
def check(ctx, expected_records: int):
    client = ctx.obj["client"]
    db = client[ctx.parent.params["database"]]
    collection = db[ctx.parent.params["collection"]]
    count = collection.count_documents(filter={})
    print(f"checking the count in the db ({count}) matches what's expected: {expected_records}")
    assert (
        count == expected_records
    ), f"expected count ({expected_records}) does not match how many records were found: {count}"
    print("successfully checked that the expected number of records was found in the db!")


@cli.command()
@click.option("--output-json", type=click.File())
@click.pass_context
def check_vector(ctx, output_json):
    """
    Checks the functionality of the vector search index by getting a score based on the
    exact result of one of the embeddings. Makes sure that the search index itself has finished
    indexing before running a query, then validated that the first item in the returned sorted
    list has a score of 1.0 given that the exact embedding is used as a match, and all others
    have a score less than 1.0.
    """
    # Get the first embedding from the output file
    json_content = json.load(output_json)
    exact_embedding = json_content[0]["embeddings"]
    client = ctx.obj["client"]
    db = client[ctx.parent.params["database"]]
    collection = db[ctx.parent.params["collection"]]
    vector_index_name = "embeddings"
    status = [ind for ind in collection.list_search_indexes() if ind["name"] == vector_index_name][
        0
    ].get("status")
    max_attempts = 30
    attempts = 0
    wait_seconds = 5
    while status != "READY" and attempts < max_attempts:
        print(
            f"status of search index: {status}, waiting another {wait_seconds} "
            f"seconds for it to be ready"
        )
        attempts += 1
        time.sleep(wait_seconds)
        status = [
            ind for ind in collection.list_search_indexes() if ind["name"] == vector_index_name
        ][0].get("status")
    print(f"search index is ready to go ({status}), checking vector content")
    pipeline = [
        {
            "$vectorSearch": {
                "index": "embeddings",
                "path": "embeddings",
                "queryVector": exact_embedding,
                "numCandidates": 150,
                "limit": 10,
            },
        },
        {"$project": {"_id": 0, "text": 1, "score": {"$meta": "vectorSearchScore"}}},
    ]
    result = list(collection.aggregate(pipeline=pipeline))
    print(f"vector query result: {result}")
    assert result[0]["score"] == 1.0, "score detected should be 1: {}".format(result[0]["score"])
    for r in result[1:]:
        assert r["score"] < 1.0, "score detected should be less than 1: {}".format(r["score"])
    print("successfully validated vector content!")


if __name__ == "__main__":
    cli()
