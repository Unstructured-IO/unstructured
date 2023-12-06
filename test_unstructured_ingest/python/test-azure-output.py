#!/usr/bin/env python
import click
from azure.storage.blob import ContainerClient


@click.group(name="azure-ingest")
def cli():
    pass


@cli.command()
@click.option("--connection-string", type=str, required=True)
@click.option("--container", type=str, required=True)
@click.option("--blob-path", type=str, required=True)
def down(connection_string: str, container: str, blob_path: str):
    container_client = ContainerClient.from_connection_string(
        conn_str=connection_string, container_name=container
    )
    blob_list = [b.name for b in list(container_client.list_blobs(name_starts_with=blob_path))]
    print(f"deleting all content from {container}/{blob_path}")
    # Delete all content in folder first
    container_client.delete_blobs(*[b for b in blob_list if b != blob_path])

    # Delete folder itself
    container_client.delete_blob(blob_path)


@cli.command()
@click.option("--connection-string", type=str, required=True)
@click.option("--container", type=str, required=True)
@click.option("--blob-path", type=str, required=True)
@click.option("--expected-files", type=int, required=True)
def check(connection_string: str, container: str, blob_path: str, expected_files: int):
    container_client = ContainerClient.from_connection_string(
        conn_str=connection_string, container_name=container
    )
    blob_json_list = [
        b.name
        for b in list(container_client.list_blobs(name_starts_with=blob_path))
        if b.name.endswith("json")
    ]
    found = len(blob_json_list)
    print(
        f"Checking that the number of files found ({found}) "
        f"matches what's expected: {expected_files}"
    )
    assert (
        found == expected_files
    ), f"number of files found ({found}) doesn't match what's expected: {expected_files}"
    print("successfully checked the number of files!")


if __name__ == "__main__":
    cli()
