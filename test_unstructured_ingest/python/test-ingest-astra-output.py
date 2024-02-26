import click
from astrapy.db import AstraDB


@click.command()
@click.option("--token", type=str)
@click.option("--api-endpoint", type=str)
@click.option("--collection-name", type=str, default="collection_test")
@click.option("--embedding-dimension", type=int, default=384)
def run_check(token, api_endpoint, collection_name, embedding_dimension):
    print(f"Checking contents of Astra DB collection: {collection_name}")

    # Initialize our vector db
    astra_db = AstraDB(token=token, api_endpoint=api_endpoint)
    astra_db_collection = astra_db.collection(collection_name)

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
    find_one = astra_db_collection.find_one()
    random_vector = find_one["data"]["document"]["$vector"]
    random_text = find_one["data"]["document"]["content"]

    # Perform a similarity search
    find_result = astra_db_collection.vector_find(random_vector, limit=1)

    # Check that we retrieved the coded cleats copy data
    assert find_result[0]["content"] == random_text
    print("Vector search complete.")

    # Clean up the collection
    astra_db.delete_collection(collection_name)

    print("Table deletion complete")


if __name__ == "__main__":
    run_check()
