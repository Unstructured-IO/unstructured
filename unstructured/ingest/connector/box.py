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
    def __post_init__(self):
        from boxsdk import JWTAuth

        super().__post_init__()
        # We are passing in a json file path via the envt. variable.
        # Need to convert that to an Oauth2 object.
        try:
            self.access_kwargs["oauth"] = JWTAuth.from_settings_file(
                self.access_kwargs["box_app_config"],
            )
        except (TypeError, ValueError, KeyError) as e:
            raise AccessTokenError(f"Problem with box_app_config: {e}")

    def __getstate__(self):
        """
        NOTE: This should not be a permanent solution.
        Multiprocessing fails when it tries to pickle some Locks in the SimpleBoxConfig.
        __getstate__ is called right before an object gets pickled.
        We are setting those attributes to None to allow pickling.
        """
        state = self.__dict__.copy()
        state["access_kwargs"]["oauth"]._refresh_lock = None
        state["access_kwargs"]["oauth"]._rsa_private_key._blinding_lock = None
        state["access_kwargs"]["oauth"]._rsa_private_key._backend = None
        state["access_kwargs"]["oauth"]._rsa_private_key._rsa_cdata = None
        state["access_kwargs"]["oauth"]._rsa_private_key._evp_pkey = None
        return state


class BoxIngestDoc(FsspecIngestDoc):
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
