from abc import ABC
from dataclasses import dataclass
from typing import Optional, TypeVar

from unstructured.ingest.enhanced_dataclass.dataclasses import enhanced_field


@dataclass
class AccessConfig:
    """Meant to designate holding any sensitive information associated with other configs
    and also for access specific configs."""


access_config_type = TypeVar("access_config_type", bound=AccessConfig)


@dataclass
class BaseConnectionConfig:
    access_config: Optional[access_config_type] = enhanced_field(sensitive=True, default=None)


config_type = TypeVar("config_type", bound=BaseConnectionConfig)


@dataclass
class BaseConnector(ABC):
    connection_config: Optional[config_type] = None
