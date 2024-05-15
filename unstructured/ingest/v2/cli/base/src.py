from dataclasses import dataclass, field
from typing import Optional, Type, TypeVar

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

CliConfigT = TypeVar("CliConfigT", bound=CliConfig)


@dataclass(kw_only=True)
class SrcCmd(BaseCmd):
    indexer_config: Optional[Type[CliConfigT]] = None
    downloader_config: Optional[Type[CliConfigT]] = None
    connection_config: Optional[Type[CliConfigT]] = None
    default_configs: list[CliConfig] = field(
        default_factory=lambda: [
            ProcessorCliConfig,
            PartitionerCliConfig,
            EmbedderCliConfig,
            ChunkerCliConfig,
        ]
    )

    def src(self, ctx: click.Context, **options):
        if ctx.invoked_subcommand:
            return

        conform_click_options(options)
        options.get("verbose", False)
        try:
            pipeline = self.get_pipline(src=self.cmd_name, source_options=options)
            logger.info(f"Running pipeline: {pipeline}")
            # pipeline.run()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e

    def get_cmd(self) -> click.Group:
        # Dynamically create the command without the use of click decorators
        fn = self.src
        fn = click.pass_context(fn)
        cmd: click.Group = click.group(fn, cls=Group)
        cmd.name = self.cmd_name
        cmd.invoke_without_command = True
        extras = [
            x for x in [self.indexer_config, self.downloader_config, self.connection_config] if x
        ]
        self.add_options(cmd, extras=extras)

        # TODO remove after v1 no longer supported
        cmd.params.append(
            click.Option(
                ["--output-dir"],
                required=True,
                type=str,
                help="Local path to write partitioned output to",
            )
        )
        return cmd
