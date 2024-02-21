import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.clarifai import (
    ClarifaiWriteConfig,
    SimpleClarifaiConfig,
)

CMD_NAME = "clarifai"

@dataclass
class ClarifaiCliConfig(SimpleClarifaiConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--api-key"],
                type=str,
                default=None,
                help="The CLARIFAI_PAT of the user to access clarifai platform apps and models",
                envvar="CLARIFAI_PAT",
                show_envvar=True
            ),
            click.Option(
                ["--app-id"],
                type=str,
                default=None,
                help="Clarifai app name/id",
            ),
            click.Option(
                ["--user-id"],
                type=str,
                default=None,
                help="Clarifai User name/ID",
            ),
        ]
        return options
    

@dataclass
class ClarifaiCliWriteConfig(ClarifaiWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.option]:
        options =[
            click.Option(
                ["--batch-size"],
                type=int,
                default=50,
                help="No of inputs upload per batch",
            ),
            click.Option(
                ["--num-processes"],
                type=int,
                default=1,
                help="No of parallel processes for upload",
            ),
        ]
        return options
def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls= BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=ClarifaiCliConfig,
        additional_cli_options=[ClarifaiCliWriteConfig],
        write_config=ClarifaiWriteConfig
    )
    return cmd_cls