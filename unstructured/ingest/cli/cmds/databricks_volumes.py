import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.databricks_volumes import (
    DatabricksVolumesWriteConfig,
    SimpleDatabricksVolumesConfig,
)

CMD_NAME = "databricks-volumes"


@dataclass
class DatabricksVolumesCliConfig(SimpleDatabricksVolumesConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(["--host"], type=str, default=None),
            click.Option(["--account-id"], type=str, default=None),
            click.Option(["--username"], type=str, default=None),
            click.Option(["--password"], type=str, default=None),
            click.Option(["--client-id"], type=str, default=None),
            click.Option(["--client-secret"], type=str, default=None),
            click.Option(["--token"], type=str, default=None),
            click.Option(["--profile"], type=str, default=None),
            click.Option(["--azure-workspace-resource-id"], type=str, default=None),
            click.Option(["--azure-client-secret"], type=str, default=None),
            click.Option(["--azure-client-id"], type=str, default=None),
            click.Option(["--azure-tenant-id"], type=str, default=None),
            click.Option(["--azure-environment"], type=str, default=None),
            click.Option(["--auth-type"], type=str, default=None),
            click.Option(["--cluster-id"], type=str, default=None),
            click.Option(["--google-credentials"], type=str, default=None),
            click.Option(["--google-service-account"], type=str, default=None),
        ]
        return options


@dataclass
class DatabricksVolumesCliWriteConfig(DatabricksVolumesWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(["--volume"], type=str, required=True),
            click.Option(["--catalog"], type=str, required=True),
            click.Option(["--volume-path"], type=str, required=False, default=None),
            click.Option(["--override"], type=bool, is_flag=True),
            click.Option(["--encoding"], type=str, required=True, default="utf-8"),
            click.Option(["--schema"], type=str, required=True, default="default"),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=DatabricksVolumesCliConfig,
        additional_cli_options=[DatabricksVolumesCliWriteConfig],
        write_config=DatabricksVolumesWriteConfig,
    )
    return cmd_cls
