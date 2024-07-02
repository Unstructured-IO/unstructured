from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.databricks_volumes import CONNECTOR_TYPE


@dataclass
class DatabricksVolumesCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--host"],
                type=str,
                default=None,
                help="The Databricks host URL for either the "
                "Databricks workspace endpoint or the "
                "Databricks accounts endpoint.",
            ),
            click.Option(
                ["--account-id"],
                type=str,
                default=None,
                help="The Databricks account ID for the Databricks "
                "accounts endpoint. Only has effect when Host is "
                "either https://accounts.cloud.databricks.com/ (AWS), "
                "https://accounts.azuredatabricks.net/ (Azure), "
                "or https://accounts.gcp.databricks.com/ (GCP).",
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
            click.Option(["--client-id"], type=str, default=None),
            click.Option(["--client-secret"], type=str, default=None),
            click.Option(
                ["--token"],
                type=str,
                default=None,
                help="The Databricks personal access token (PAT) (AWS, Azure, and GCP) or "
                "Azure Active Directory (Azure AD) token (Azure).",
            ),
            click.Option(
                ["--azure-workspace-resource-id"],
                type=str,
                default=None,
                help="The Azure Resource Manager ID for the Azure Databricks workspace, "
                "which is exchanged for a Databricks host URL.",
            ),
            click.Option(
                ["--azure-client-secret"],
                type=str,
                default=None,
                help="The Azure AD service principal’s client secret.",
            ),
            click.Option(
                ["--azure-client-id"],
                type=str,
                default=None,
                help="The Azure AD service principal’s application ID.",
            ),
            click.Option(
                ["--azure-tenant-id"],
                type=str,
                default=None,
                help="The Azure AD service principal’s tenant ID.",
            ),
            click.Option(
                ["--azure-environment"],
                type=str,
                default=None,
                help="The Azure environment type (such as Public, UsGov, China, and Germany) for a "
                "specific set of API endpoints. Defaults to PUBLIC.",
            ),
            click.Option(
                ["--auth-type"],
                type=str,
                default=None,
                help="When multiple auth attributes are available in the "
                "environment, use the auth type specified by this "
                "argument. This argument also holds the currently "
                "selected auth.",
            ),
            click.Option(["--cluster-id"], type=str, default=None),
            click.Option(["--google-credentials"], type=str, default=None),
            click.Option(["--google-service-account"], type=str, default=None),
        ]
        return options


@dataclass
class DatabricksVolumesCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--volume"], type=str, required=True, help="Name of volume in the Unity Catalog"
            ),
            click.Option(
                ["--catalog"],
                type=str,
                required=True,
                help="Name of the catalog in the Databricks Unity Catalog service",
            ),
            click.Option(
                ["--volume-path"],
                type=str,
                required=False,
                default=None,
                help="Optional path within the volume to write to",
            ),
            click.Option(
                ["--overwrite"],
                type=bool,
                is_flag=True,
                help="If true, an existing file will be overwritten.",
            ),
            click.Option(
                ["--encoding"],
                type=str,
                required=True,
                default="utf-8",
                help="Encoding applied to the data when written to the volume",
            ),
            click.Option(
                ["--schema"],
                type=str,
                required=True,
                default="default",
                help="Schema associated with the volume to write to in the Unity Catalog service",
            ),
        ]
        return options


@dataclass
class DatabricksVolumesCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


databricks_volumes_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=DatabricksVolumesCliConnectionConfig,
    uploader_config=DatabricksVolumesCliUploaderConfig,
    upload_stager_config=DatabricksVolumesCliUploadStagerConfig,
)
