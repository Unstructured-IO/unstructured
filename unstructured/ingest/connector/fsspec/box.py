"""
Box Connector
Box does not make it simple to download files with an App.
First of all, this does not work with a free Box account.
Make sure the App service email is a collaborator for your folder (co-owner or editor)
Make sure you have the 'write all files' application scope
Maybe check 'Make api calls as the as-user header'
REAUTHORIZE app after making any of the above changes
"""

import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.fsspec.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    FsspecWriteConfig,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import AccessConfig
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


class AccessTokenError(Exception):
    """There is a problem with the Access Token."""


@dataclass
class BoxWriteConfig(FsspecWriteConfig):
    pass


@dataclass
class BoxAccessConfig(AccessConfig):
    box_app_config: t.Optional[str] = None


@dataclass
class SimpleBoxConfig(SimpleFsspecConfig):
    access_config: BoxAccessConfig = None

    @requires_dependencies(["boxfs"], extras="box")
    def get_access_config(self) -> dict:
        # Return access_kwargs with oauth. The oauth object can not be stored directly in the config
        # because it is not serializable.
        from boxsdk import JWTAuth

        access_kwargs_with_oauth: dict[str, t.Any] = {
            "oauth": JWTAuth.from_settings_file(
                self.access_config.box_app_config,
            ),
        }
        access_config: dict[str, t.Any] = self.access_config.to_dict()
        access_config.pop("box_app_config", None)
        access_kwargs_with_oauth.update(access_config)

        return access_kwargs_with_oauth


@dataclass
class BoxIngestDoc(FsspecIngestDoc):
    connector_config: SimpleBoxConfig
    registry_name: str = "box"

    @SourceConnectionError.wrap
    @requires_dependencies(["boxfs", "fsspec"], extras="box")
    def get_file(self):
        super().get_file()


@dataclass
class BoxSourceConnector(FsspecSourceConnector):
    connector_config: SimpleBoxConfig

    @requires_dependencies(["boxfs"], extras="box")
    def check_connection(self):
        from boxfs import BoxFileSystem

        try:
            BoxFileSystem(**self.connector_config.get_access_config())
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[BoxIngestDoc] = BoxIngestDoc


@dataclass
class BoxDestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleBoxConfig
    write_config: BoxWriteConfig

    @requires_dependencies(["boxfs", "fsspec"], extras="box")
    def initialize(self):
        super().initialize()

    @requires_dependencies(["boxfs"], extras="box")
    def check_connection(self):
        from boxfs import BoxFileSystem

        try:
            BoxFileSystem(**self.connector_config.get_access_config())
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")
