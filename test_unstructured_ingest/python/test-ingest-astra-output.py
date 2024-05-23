#!/usr/bin/env python
import click
from astrapy.db import AstraDB


def get_client(token, api_endpoint, collection_name) -> AstraDB:
    # Initialize our vector db
    astra_db = AstraDB(token=token, api_endpoint=api_endpoint)
    astra_db_collection = astra_db.collection(collection_name)
    return astra_db, astra_db_collection


@click.group(name="astra-ingest")
@click.option("--token", type=str)
@click.option("--api-endpoint", type=str)
@click.option("--collection-name", type=str, default="collection_test")
@click.option("--embedding-dimension", type=int, default=384)
@click.pass_context
def cli(ctx, token: str, api_endpoint: str, collection_name: str, embedding_dimension: int):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    ctx.ensure_object(dict)

    ctx.obj["db"], ctx.obj["collection"] = get_client(token, api_endpoint, collection_name)


@cli.command()
@click.pass_context
def check(ctx):
    collection_name = ctx.parent.params["collection_name"]
    print(f"Checking contents of Astra DB collection: {collection_name}")

    astra_db_collection = ctx.obj["collection"]

    # Tally up the embeddings
    docs_count = astra_db_collection.count_documents()
    number_of_embeddings = docs_count["status"]["count"]

    # Print the results
    expected_embeddings = 3
    print(
        f"# of embeddings in collection vs expected: {number_of_embeddings}/{expected_embeddings}"
    )

    # Check that the assertion is true
    assert number_of_embeddings == expected_embeddings, (
        f"Number of rows in generated table ({number_of_embeddings})"
        f"doesn't match expected value: {expected_embeddings}"
    )

    # Grab an embedding from the collection and search against itself
    # Should get the same document back as the most similar
    find_one = astra_db_collection.find_one(projection={"*": 1})
    random_vector = find_one["data"]["document"]["$vector"]
    random_text = find_one["data"]["document"]["content"]

    # Perform a similarity search
    find_result = astra_db_collection.vector_find(
        random_vector,
        limit=1,
        fields=["*"],
    )

    # Check that we retrieved the coded cleats copy data
    assert find_result[0]["content"] == random_text
    print("Vector search complete.")


@cli.command()
@click.pass_context
def down(ctx):
    astra_db = ctx.obj["db"]
    collection_name = ctx.parent.params["collection_name"]
    print(f"deleting collection: {collection_name}")
    astra_db.delete_collection(collection_name)
    print(f"successfully deleted collection: {collection_name}")


if __name__ == "__main__":
    cli()
