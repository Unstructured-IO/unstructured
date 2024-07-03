from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.azure_cognitive_search import CONNECTOR_TYPE


@dataclass
class AzureCognitiveSearchCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--index"],
                required=True,
                type=str,
                help="The name of the Azure AI (Cognitive) Search index to connect to.",
                envvar="AZURE_SEARCH_INDEX",
                show_envvar=True,
            ),
            click.Option(
                ["--endpoint"],
                required=True,
                type=str,
                help="The URL endpoint of an Azure AI (Cognitive) search service."
                "In the form of https://{{service_name}}.search.windows.net",
                envvar="AZURE_SEARCH_ENDPOINT",
                show_envvar=True,
            ),
            click.Option(
                ["--key"],
                required=True,
                type=str,
                help="Credential that is used for authenticating to an Azure service."
                "(is an AzureKeyCredential)",
                envvar="AZURE_SEARCH_API_KEY",
                show_envvar=True,
            ),
        ]
        return options


@dataclass
class AzureCognitiveSearchCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


@dataclass
class AzureCognitiveSearchCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


azure_cognitive_search_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=AzureCognitiveSearchCliConnectionConfig,
    uploader_config=AzureCognitiveSearchCliUploaderConfig,
    upload_stager_config=AzureCognitiveSearchCliUploadStagerConfig,
)
