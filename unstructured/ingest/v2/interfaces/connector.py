from abc import ABC
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field


@dataclass
class AccessConfig(EnhancedDataClassJsonMixin):
    """Meant to designate holding any sensitive information associated with other configs
    and also for access specific configs."""


AccessConfigT = TypeVar("AccessConfigT", bound=AccessConfig)


@dataclass
class ConnectionConfig(EnhancedDataClassJsonMixin):
    access_config: Optional[AccessConfigT] = enhanced_field(sensitive=True, default=None)

    def get_access_config(self) -> dict[str, Any]:
        if not self.access_config:
            return {}
        return self.access_config.to_dict(apply_name_overload=False)


ConnectionConfigT = TypeVar("ConnectionConfigT", bound=ConnectionConfig)


@dataclass
class BaseConnector(ABC):
    connection_config: Optional[ConnectionConfigT] = None
