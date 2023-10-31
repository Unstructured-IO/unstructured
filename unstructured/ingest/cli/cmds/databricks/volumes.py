import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.cmds.databricks.base_src import DatabricksSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class DatabricksVolumesCliConfig(BaseConfig, CliMixin):
    host: t.Optional[str]
    account_id: t.Optional[str]
    token: t.Optional[str]
    username: t.Optional[str]
    password: t.Optional[str]

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--host"],
                type=str,
                help="The Databricks host URL for either the Databricks workspace "
                "endpoint or the Databricks accounts endpoint.",
            ),
            click.Option(
                ["--account-id"],
                type=str,
                help="The Databricks account ID for the Databricks accounts endpoint. "
                "Only has effect when Host is either "
                "https://accounts.cloud.databricks.com/ (AWS), "
                "https://accounts.azuredatabricks.net/ (Azure), "
                "or https://accounts.gcp.databricks.com/ (GCP).",
            ),
            click.Option(
                ["--token"],
                type=str,
                help="The Databricks personal access token (PAT) (AWS, Azure, and GCP) "
                "or Azure Active Directory (Azure AD) token (Azure).",
            ),
            click.Option(
                ["--username"],
                default=None,
                type=str,
                help="The Databricks username part of basic authentication. "
                "Only possible when Host is *.cloud.databricks.com (AWS).",
            ),
            click.Option(
                ["--password"],
                type=str,
                help="The Databricks password part of basic authentication. "
                "Only possible when Host is *.cloud.databricks.com (AWS).",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = DatabricksSrcCmd(
        cmd_name="databricks-volumes", additional_cli_options=[DatabricksVolumesCliConfig]
    )
    return cmd_cls
