"""
Box Connector
Box does not make it simple to download files with an App.
First of all, this does not work with a free Box account.
Make sure the App service email is a collaborator for your folder (co-owner or editor)
Make sure you have the 'write all files' application scope
Maybe check 'Make api calls as the as-user header'
REAUTHORIZE app after making any of the above changes
"""

from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.ingest.interfaces import StandardConnectorConfig
from unstructured.utils import requires_dependencies


class AccessTokenError(Exception):
    """There is a problem with the Access Token."""


@dataclass
class SimpleBoxConfig(SimpleFsspecConfig):
    @requires_dependencies(["boxfs"], extras="box")
    def get_access_kwargs(self):
        # Return access_kwargs with oauth. The oauth object can not be stored directly in the config
        # because it is not serializable.
        from boxsdk import JWTAuth

        access_kwargs_with_oauth = {
            "oauth": JWTAuth.from_settings_file(
                self.access_kwargs["box_app_config"],
            ),
        }
        access_kwargs_with_oauth.update(self.access_kwargs)
        return access_kwargs_with_oauth


@dataclass
class BoxIngestDoc(FsspecIngestDoc):
    config: SimpleBoxConfig
    registry_name: str = "box"

    @requires_dependencies(["boxfs", "fsspec"], extras="box")
    def get_file(self):
        super().get_file()


@requires_dependencies(["boxfs", "fsspec"], extras="box")
class BoxConnector(FsspecConnector):
    ingest_doc_cls: Type[BoxIngestDoc] = BoxIngestDoc

    def __init__(
        self,
        config: SimpleBoxConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)
