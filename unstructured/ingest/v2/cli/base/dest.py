from dataclasses import dataclass
from typing import Optional, Type, TypeVar

import click

from unstructured.ingest.cli.utils import conform_click_options
from unstructured.ingest.v2.cli.base.cmd import BaseCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.logger import logger

CliConfigT = TypeVar("CliConfigT", bound=CliConfig)


@dataclass(kw_only=True)
class DestCmd(BaseCmd):
    connection_config: Optional[Type[CliConfigT]] = None
    uploader_config: Optional[Type[CliConfigT]] = None
    upload_stager_config: Optional[Type[CliConfigT]] = None

    def dest(self, ctx: click.Context, **options):
        if not ctx.parent:
            raise click.ClickException("destination command called without a parent")
        if not ctx.parent.info_name:
            raise click.ClickException("parent command missing info name")
        source_cmd = ctx.parent.info_name.replace("-", "_")
        source_options: dict = ctx.parent.params if ctx.parent else {}
        conform_click_options(options)
        try:
            pipeline = self.get_pipline(
                src=source_cmd,
                source_options=source_options,
                dest=self.cmd_name,
                destination_options=options,
            )
            pipeline.run()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e

    def get_cmd(self) -> click.Command:
        # Dynamically create the command without the use of click decorators
        fn = self.dest
        fn = click.pass_context(fn)
        cmd: click.Group = click.command(fn)
        cmd.name = self.cmd_name
        cmd.invoke_without_command = True
        extras = [
            x
            for x in [self.uploader_config, self.upload_stager_config, self.connection_config]
            if x
        ]
        self.add_options(cmd, extras=extras)
        return cmd
