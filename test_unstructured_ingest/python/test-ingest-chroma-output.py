import click
import chromadb


@click.command()
@click.option("--client", type=str)
@click.option("--collection-name", type=str)
def run_check(client, collection_name):
    print(f"Checking contents of Chroma collection: {collection_name}")

    chroma_client = chromadb.PersistentClient(path=client)

    collection = chroma_client.get_or_create_collection(name=collection_name)

    number_of_embeddings = collection.count()
    expected_embeddings = 3
    print(
        f"Number of embeddings in collection vs expected: {number_of_embeddings}/{expected_embeddings}"
    )

    assert number_of_embeddings == expected_embeddings, (
        f"Number of rows in generated table ({number_of_embeddings}) "
        f"doesn't match expected value: {expected_embeddings}"
    )

    print("Table check complete")
    


if __name__ == "__main__":
    run_check()
