import typing as t
from dataclasses import dataclass

from unstructured.ingest.cli.base.dest import BaseDestCmd
from unstructured.ingest.cli.cmds.databricks.interfaces import AuthConfig
from unstructured.ingest.cli.cmds.databricks.utils import print_experimental_banner
from unstructured.ingest.cli.interfaces import CliFilesStorageConfig
from unstructured.ingest.interfaces import BaseConfig, DatabricksVolumesConfig


@dataclass
class DatabricksDestCmd(BaseDestCmd):
    cli_config: t.Optional[t.Type[BaseConfig]] = CliFilesStorageConfig
    auth_cli_config: t.Optional[t.Type[BaseConfig]] = None
    experimental: bool = True

    def __post_init__(self):
        # Due to python3.8 limitation, required fields can't be added in children dataclasses
        if self.auth_cli_config is None:
            raise ValueError("auth_cli_config required")
        self.additional_cli_options.append(self.auth_cli_config)
        self.addition_configs["databricks_volume_config"] = DatabricksVolumesConfig
        self.addition_configs["auth_configs"] = self.auth_cli_config

    def get_dest_runner(self, source_cmd: str, options: dict, parent_options: dict):
        runner = super().get_dest_runner(
            source_cmd=source_cmd, options=options, parent_options=parent_options
        )
        if "auth_configs" in runner.writer_kwargs and isinstance(
            runner.writer_kwargs["auth_configs"], AuthConfig
        ):
            runner.writer_kwargs["auth_configs"] = runner.writer_kwargs["auth_configs"].to_dict()
        if self.experimental:
            print_experimental_banner()
        return runner

    @property
    def cmd_name_key(self):
        return "databricks_volumes"
