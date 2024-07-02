from abc import ABC
from dataclasses import dataclass
from typing import Any, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin


@dataclass
class AccessConfig(EnhancedDataClassJsonMixin):
    """Meant to designate holding any sensitive information associated with other configs
    and also for access specific configs."""


AccessConfigT = TypeVar("AccessConfigT", bound=AccessConfig)


@dataclass
class ConnectionConfig(EnhancedDataClassJsonMixin):
    access_config: AccessConfigT

    def get_access_config(self) -> dict[str, Any]:
        if not self.access_config:
            return {}
        return self.access_config.to_dict(apply_name_overload=False)


ConnectionConfigT = TypeVar("ConnectionConfigT", bound=ConnectionConfig)


@dataclass
class BaseConnector(ABC):
    connection_config: ConnectionConfigT
