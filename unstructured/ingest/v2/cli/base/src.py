import logging
from dataclasses import dataclass, field
from typing import Optional, Type

import click

from unstructured.ingest.cli.utils import Group, conform_click_options
from unstructured.ingest.v2.cli.base.cmd import BaseCmd
from unstructured.ingest.v2.cli.configs import (
    ChunkerCliConfig,
    EmbedderCliConfig,
    PartitionerCliConfig,
    ProcessorCliConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.logger import logger


@dataclass
class SrcCmd(BaseCmd):
    indexer_config: Optional[Type[CliConfig]] = None
    downloader_config: Optional[Type[CliConfig]] = None
    connection_config: Optional[Type[CliConfig]] = None
    default_configs: list[CliConfig] = field(
        default_factory=lambda: [
            ProcessorCliConfig,
            PartitionerCliConfig,
            EmbedderCliConfig,
            ChunkerCliConfig,
        ]
    )

    def cmd(self, ctx: click.Context, **options) -> None:
        if ctx.invoked_subcommand:
            return

        conform_click_options(options)
        logger.setLevel(logging.DEBUG if options.get("verbose", False) else logging.INFO)
        try:
            pipeline = self.get_pipline(src=self.cmd_name, source_options=options)
            pipeline.run()
        except Exception as e:
            logger.error(f"failed to run source command {self.cmd_name}: {e}", exc_info=True)
            raise click.ClickException(str(e)) from e

    def get_cmd(self) -> click.Group:
        # Dynamically create the command without the use of click decorators
        fn = self.cmd
        fn = click.pass_context(fn)
        cmd = click.group(fn, cls=Group)
        if not isinstance(cmd, click.core.Group):
            raise ValueError(f"generated src command was not of expected type Group: {type(cmd)}")
        cmd.name = self.cmd_name
        cmd.short_help = "v2"
        cmd.invoke_without_command = True
        extras = [
            x for x in [self.indexer_config, self.downloader_config, self.connection_config] if x
        ]
        self.add_options(cmd, extras=extras)

        # TODO remove after v1 no longer supported
        cmd.params.append(
            click.Option(
                ["--output-dir"],
                required=False,
                type=str,
                help="Local path to write partitioned output to",
            )
        )
        return cmd
