import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.cmds.databricks.base_src import DatabricksSrcCmd
from unstructured.ingest.cli.cmds.databricks.interfaces import (
    AuthConfig,
    DatabricksVolumesWriteConfig,
)

CMD_NAME = "databricks-volumes"


@dataclass
class DatabricksVolumesCliConfig(AuthConfig):
    host: t.Optional[str] = None
    account_id: t.Optional[str] = None
    token: t.Optional[str] = None
    username: t.Optional[str] = None
    password: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--host"],
                type=str,
                default=None,
                help="The Databricks host URL for either the Databricks workspace "
                "endpoint or the Databricks accounts endpoint.",
            ),
            click.Option(
                ["--account-id"],
                type=str,
                default=None,
                help="The Databricks account ID for the Databricks accounts endpoint. "
                "Only has effect when Host is either "
                "https://accounts.cloud.databricks.com/ (AWS), "
                "https://accounts.azuredatabricks.net/ (Azure), "
                "or https://accounts.gcp.databricks.com/ (GCP).",
            ),
            click.Option(
                ["--token"],
                type=str,
                default=None,
                help="The Databricks personal access token (PAT) (AWS, Azure, and GCP) "
                "or Azure Active Directory (Azure AD) token (Azure).",
            ),
            click.Option(
                ["--username"],
                type=str,
                default=None,
                help="The Databricks username part of basic authentication. "
                "Only possible when Host is *.cloud.databricks.com (AWS).",
            ),
            click.Option(
                ["--password"],
                type=str,
                default=None,
                help="The Databricks password part of basic authentication. "
                "Only possible when Host is *.cloud.databricks.com (AWS).",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = DatabricksSrcCmd(cmd_name=CMD_NAME, auth_cli_config=DatabricksVolumesCliConfig)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.cmds.databricks.base_dest import DatabricksDestCmd

    cmd_cls = DatabricksDestCmd(
        cmd_name=CMD_NAME,
        auth_cli_config=DatabricksVolumesCliConfig,
        additional_cli_options=[DatabricksVolumesWriteConfig],
    )
    return cmd_cls
