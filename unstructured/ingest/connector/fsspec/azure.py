import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.fsspec.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    FsspecWriteConfig,
    SimpleFsspecConfig,
    WriteTextConfig,
)
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import AccessConfig
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class AzureWriteTextConfig(WriteTextConfig):
    overwrite: bool = False


@dataclass
class AzureWriteConfig(FsspecWriteConfig):
    write_text_config: t.Optional[AzureWriteTextConfig] = None


@dataclass
class AzureAccessConfig(AccessConfig):
    account_name: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    account_key: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    connection_string: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    sas_token: t.Optional[str] = enhanced_field(default=None, sensitive=True)


@dataclass
class SimpleAzureBlobStorageConfig(SimpleFsspecConfig):
    access_config: AzureAccessConfig = None


@dataclass
class AzureBlobStorageIngestDoc(FsspecIngestDoc):
    connector_config: SimpleAzureBlobStorageConfig
    registry_name: str = "azure"

    @SourceConnectionError.wrap
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def get_file(self):
        super().get_file()


@dataclass
class AzureBlobStorageSourceConnector(FsspecSourceConnector):
    connector_config: SimpleAzureBlobStorageConfig

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc


@dataclass
class AzureBlobStorageDestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleAzureBlobStorageConfig
    write_config: AzureWriteConfig

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def initialize(self):
        super().initialize()

    @requires_dependencies(["adlfs"], extras="azure")
    def check_connection(self):
        from adlfs import AzureBlobFileSystem

        try:
            AzureBlobFileSystem(**self.connector_config.get_access_config())
        except ValueError as connection_error:
            logger.error(f"failed to validate connection: {connection_error}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {connection_error}")
