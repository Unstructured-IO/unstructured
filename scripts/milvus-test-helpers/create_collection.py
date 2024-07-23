#!/usr/bin/env python3
import pprint
import sys

import click

# from pymilvus import (
#     CollectionSchema,
#     DataType,
#     FieldSchema,
#     MilvusClient,
# )
# from pymilvus.milvus_client import IndexParams

print("within python script")
print(sys.executable)
pprint.pprint(sys.modules)

if 1 == 1:
    from pymilvus import (
        CollectionSchema,
        DataType,
        FieldSchema,
        MilvusClient,
    )
    from pymilvus.milvus_client import IndexParams


def get_schema() -> CollectionSchema:
    id_field = FieldSchema(
        name="id", dtype=DataType.INT64, descrition="primary field", is_primary=True, auto_id=True
    )
    embeddings_field = FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=384)

    schema = CollectionSchema(
        enable_dynamic_field=True,
        fields=[
            id_field,
            embeddings_field,
        ],
    )

    return schema


def get_index_params() -> IndexParams:
    index_params = IndexParams()
    index_params.add_index(field_name="embeddings", index_type="AUTOINDEX", metric_type="COSINE")
    return index_params


def create_database(client: MilvusClient, db_name: str) -> None:
    databases = client._get_connection().list_database()
    if db_name in databases:
        drop_database(client=client, db_name=db_name)
    print(f"Creating database {db_name}")
    client._get_connection().create_database(db_name=db_name)
    client.using_database(db_name=db_name)


def drop_database(client: MilvusClient, db_name: str) -> None:
    print("Dropping existing database first")
    client.using_database(db_name=db_name)
    collections = client.list_collections()
    for collection in collections:
        print(f"Dropping existing collection {collection} first")
        client.drop_collection(collection_name=collection)
    client._get_connection().drop_database(db_name=db_name)


def create_collection(client: MilvusClient, collection_name: str) -> None:
    collections = client.list_collections()
    if collection_name in collections:
        print("Dropping existing collection first")
        client.drop_collection(collection_name=collection_name)
    schema = get_schema()
    index_params = get_index_params()
    print(f"Creating collection {collection_name}")
    client.create_collection(
        collection_name=collection_name, schema=schema, index_params=index_params
    )


@click.command("milvus-init")
@click.option("--host", type=str, default="localhost")
@click.option("--port", type=int, default=19530)
# @click.option("--db-name", type=str, default="milvus")
@click.option("--db-name", type=str, default="ingest_test_db")
def create(host: str, port: int, db_name: str):
    client = MilvusClient(uri=f"http://{host}:{port}")
    create_database(client=client, db_name=db_name)
    create_collection(client=client, collection_name="ingest_test")


if __name__ == "__main__":
    create()
