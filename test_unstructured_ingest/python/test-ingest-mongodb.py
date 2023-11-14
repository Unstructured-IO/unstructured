#!/usr/bin/env python
import click
from pymongo.mongo_client import MongoClient


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
    pass


@cli.command()
@click.pass_context
def up(ctx):
    client = get_client(ctx.parent.params["uri"])
    collection_name = ctx.parent.params["collection"]
    db = client[ctx.parent.params["database"]]
    print(f"creating collection {collection_name}")
    db.create_collection(name=collection_name)
    print(f"successfully created collection: {collection_name}")


@cli.command()
@click.pass_context
def down(ctx):
    collection_name = ctx.parent.params["collection"]
    client = get_client(ctx.parent.params["uri"])
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
    client = get_client(ctx.parent.params["uri"])
    db = client[ctx.parent.params["database"]]
    collection = db[ctx.parent.params["collection"]]
    count = collection.count_documents(filter={})
    print(f"checking the count in the db ({count}) matches what's expected: {expected_records}")
    assert (
        count == expected_records
    ), f"expected count ({expected_records}) does not match how many records were found: {count}"
    print("successfully checked that the expected number of records was found in the db")


if __name__ == "__main__":
    cli()
