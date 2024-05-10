from abc import ABC
from dataclasses import dataclass
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class BaseUploadStagerConfig:
    pass


config_type = TypeVar("config_type", bound=BaseUploadStagerConfig)


@dataclass
class UploadStager(BaseProcess, ABC):
    upload_config: Optional[config_type] = None
