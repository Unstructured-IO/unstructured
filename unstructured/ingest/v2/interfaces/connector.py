from abc import ABC
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field


@dataclass
class AccessConfig(EnhancedDataClassJsonMixin):
    """Meant to designate holding any sensitive information associated with other configs
    and also for access specific configs."""


access_config_type = TypeVar("access_config_type", bound=AccessConfig)


@dataclass
class ConnectionConfig:
    access_config: Optional[access_config_type] = enhanced_field(sensitive=True, default=None)

    def get_access_config(self) -> dict[str, Any]:
        if not self.access_config:
            return {}
        return self.access_config.to_dict(apply_name_overload=False)


config_type = TypeVar("config_type", bound=ConnectionConfig)


@dataclass
class BaseConnector(ABC):
    connection_config: Optional[config_type] = None
