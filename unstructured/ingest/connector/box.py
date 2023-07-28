"""
Make sure the app is a collaborator for your folder (maybe as co-owner, but editor shoud be fine)
Make sure you have write all files to download
Maybe check Make api calls as the as-user header
REAUTHORIZE the app after making any changes.



"""

import json
from dataclasses import dataclass, field
from typing import Type

from boxsdk import JWTAuth

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.ingest.interfaces import StandardConnectorConfig
from unstructured.utils import requires_dependencies


@dataclass
class SimpleBoxConfig(SimpleFsspecConfig):
    def __post_init__(self):
        super().__post_init__()
        # We are passing in a jwt json string via command line. Need to convert that to an Oauth2 object.
        self.access_kwargs["oauth"] = JWTAuth.from_settings_dictionary(json.loads(self.access_kwargs["oauth_json"]))
        del self.access_kwargs["oauth_json"] # String is no longer needed.
    
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
