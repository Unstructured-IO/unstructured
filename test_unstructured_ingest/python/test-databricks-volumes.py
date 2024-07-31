#!/usr/bin/env python
import json

import click
from databricks.sdk import WorkspaceClient


@click.group()
def cli():
    pass


def _get_volume_path(catalog: str, volume: str, volume_path: str):
    return f"/Volumes/{catalog}/default/{volume}/{volume_path}"


@cli.command()
@click.option("--host", type=str, required=True)
@click.option("--username", type=str, required=True)
@click.option("--password", type=str, required=True)
@click.option("--catalog", type=str, required=True)
@click.option("--volume", type=str, required=True)
@click.option("--volume-path", type=str, required=True)
def test(
    host: str,
    username: str,
    password: str,
    catalog: str,
    volume: str,
    volume_path: str,
):
    client = WorkspaceClient(host=host, username=username, password=password)
    files = list(
        client.files.list_directory_contents(_get_volume_path(catalog, volume, volume_path))
    )

    assert len(files) == 1

    resp = client.files.download(files[0].path)
    data = json.loads(resp.contents.read())

    assert len(data) == 5
    assert [v["type"] for v in data] == [
        "UncategorizedText",
        "Title",
        "NarrativeText",
        "UncategorizedText",
        "Title",
    ]

    print("Databricks test passed!")


@cli.command()
@click.option("--host", type=str, required=True)
@click.option("--username", type=str, required=True)
@click.option("--password", type=str, required=True)
@click.option("--catalog", type=str, required=True)
@click.option("--volume", type=str, required=True)
@click.option("--volume-path", type=str, required=True)
def cleanup(
    host: str,
    username: str,
    password: str,
    catalog: str,
    volume: str,
    volume_path: str,
):
    client = WorkspaceClient(host=host, username=username, password=password)

    for file in client.files.list_directory_contents(
        _get_volume_path(catalog, volume, volume_path)
    ):
        client.files.delete(file.path)
    client.files.delete_directory(_get_volume_path(catalog, volume, volume_path))


if __name__ == "__main__":
    cli()
