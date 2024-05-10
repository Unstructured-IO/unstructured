from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.upload_stager import UploadStager
from unstructured.ingest.v2.interfaces.uploader import Uploader

uploader_type = TypeVar("uploader_type", bound=Uploader)
stager_type = TypeVar("stager_type", bound=UploadStager)


@dataclass(kw_only=True)
class Destination(BaseConnector, ABC):
    connector_type: str
    uploader: uploader_type
    stager: Optional[stager_type] = None

    @abstractmethod
    def check_connection(self):
        pass
