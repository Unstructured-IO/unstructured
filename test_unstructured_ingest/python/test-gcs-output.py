#!/usr/bin/env python
import click
from google.cloud import storage
from google.oauth2 import service_account


@click.group(name="gcs-ingest")
def cli():
    pass


@cli.command()
@click.option("--service-account-file", type=click.Path(), required=True)
@click.option("--bucket", type=str, required=True)
@click.option("--blob-path", type=str, required=True)
def down(service_account_file: str, bucket: str, blob_path: str):
    credentials = service_account.Credentials.from_service_account_file(
        filename=service_account_file
    )

    storage_client = storage.Client(credentials=credentials)
    for blob in storage_client.list_blobs(bucket_or_name=bucket, prefix=blob_path):
        print(f"deleting {blob.name}")
        blob.delete()


@cli.command()
@click.option("--service-account-file", type=click.Path(), required=True)
@click.option("--bucket", type=str, required=True)
@click.option("--blob-path", type=str, required=True)
@click.option("--expected-files", type=int, required=True)
def check(service_account_file: str, bucket: str, blob_path: str, expected_files: int):
    credentials = service_account.Credentials.from_service_account_file(
        filename=service_account_file
    )

    storage_client = storage.Client(credentials=credentials)
    blob_json_list = [
        f.name
        for f in storage_client.list_blobs(bucket_or_name=bucket, prefix=blob_path)
        if f.name.endswith("json")
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
