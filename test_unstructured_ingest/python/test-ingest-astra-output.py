import click

from astrapy.db import AstraDB

@click.command()
@click.option("--token", type=str)
@click.option("--api-endpoint", type=str)
@click.option("--collection-name", type=str, default="collection_test")
def run_check(token, api_endpoint, collection_name):
    print(f"Checking contents of Astra DB collection: {collection_name}")

    # Initialize our vector db
    astra_db = AstraDB(token=token, api_endpoint=api_endpoint)
    astra_db.delete_collection(collection_name)
    astra_db_collection = astra_db.create_collection(collection_name, dimension=5)

    # Insert a document into the test collection
    astra_db_collection.insert_one(
        {
            "_id": "1",
            "name": "Coded Cleats Copy",
            "description": "ChatGPT integrated sneakers that talk to you",
            "$vector": [0.25, 0.25, 0.25, 0.25, 0.25],
        }
    )

    # Tally up the embeddings
    docs_count = astra_db_collection.count_documents()
    number_of_embeddings = docs_count["status"]["count"]

    # Print the results
    expected_embeddings = 1
    print(
        f"# of embeddings in collection vs expected: {number_of_embeddings}/{expected_embeddings}"
    )

    # Check that the assertion is true
    assert number_of_embeddings == expected_embeddings, (
        f"Number of rows in generated table ({number_of_embeddings}) "
        f"doesn't match expected value: {expected_embeddings}"
    )

    # Perform a similarity search
    find_result = astra_db_collection.vector_find([0.1, 0.1, 0.2, 0.5, 1], limit=3)

    # Check that we retrieved the coded cleats copy data
    assert find_result[0]["name"] == "Coded Cleats Copy"

    # Clean up the collection
    astra_db.delete_collection(collection_name)

    print("Table check complete")


if __name__ == "__main__":
    run_check()
