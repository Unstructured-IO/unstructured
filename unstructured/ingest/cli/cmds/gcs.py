import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.base_cmd import BaseCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class GcsCliConfig(BaseConfig, CliMixin):
    token: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                default=None,
                help="Token used to access Google Cloud. GCSFS will attempt to use your "
                "default gcloud creds or get creds from the google metadata service "
                "or fall back to anonymous access.",
            ),
        ]
        return options


def get_base_cmd() -> BaseCmd:
    cmd_cls = BaseCmd(cmd_name="gcs", cli_config=GcsCliConfig, is_fsspec=True)
    return cmd_cls
