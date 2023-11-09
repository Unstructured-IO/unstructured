import typing as t
from abc import ABC
from dataclasses import dataclass, field

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class BaseCmd(ABC):
    cmd_name: str
    cli_config: t.Optional[t.Type[BaseConfig]] = None
    additional_cli_options: t.List[t.Type[CliConfig]] = field(default_factory=list)
    addition_configs: t.Dict[str, t.Type[BaseConfig]] = field(default_factory=dict)
    is_fsspec: bool = False

    @property
    def cmd_name_key(self):
        return self.cmd_name.replace("-", "_")
