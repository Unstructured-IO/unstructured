import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliMixin, DelimitedString
from unstructured.ingest.interfaces import BaseConfig

CMD_NAME = "weaviate"


@dataclass
class WeaviateCliWriteConfig(BaseConfig, CliMixin):
    host_url: str
    class_name: str
    auth_keys: t.Optional[t.List[str]] = None
    additional_keys: t.Optional[t.List[str]] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--host-url"],
                required=True,
                help="Weaviate instance url",
            ),
            click.Option(
                ["--class-name"],
                default=None,
                type=str,
                help="Class to ",
            ),
            click.Option(
                ["--auth-keys"],
                required=False,
                type=DelimitedString(),
                help="List of env variables to pull auth keys from. "
                "These keys are used to authenticate the client.",
            ),
            click.Option(
                ["--additional-keys"],
                is_flag=True,
                default=False,
                type=DelimitedString(),
                help="Additional env vars to initialize the weaviate client with.",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=WeaviateCliWriteConfig,
    )
    return cmd_cls
