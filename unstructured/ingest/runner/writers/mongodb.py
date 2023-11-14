import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector


def mongodb_writer(
    database: str,
    collection: str,
    upsert: bool = False,
    uri: t.Optional[str] = None,
    host: t.Optional[str] = None,
    port: int = 27017,
    client_params: t.Optional[t.Dict[str, t.Any]] = None,
    verbose: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    client_params = client_params if client_params else {}
    from unstructured.ingest.connector.mongodb import (
        MongoDBDestinationConnector,
        MongoDBWriteConfig,
        SimpleMongoDBStorageConfig,
    )

    return MongoDBDestinationConnector(
        write_config=MongoDBWriteConfig(database=database, collection=collection),
        connector_config=SimpleMongoDBStorageConfig(
            uri=uri, host=host, port=port, client_params=client_params
        ),
    )
