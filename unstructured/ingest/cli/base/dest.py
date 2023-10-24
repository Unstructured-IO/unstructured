import logging
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.cmd import BaseCmd
from unstructured.ingest.cli.cmd_factory import get_src_cmd
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliFilesStorageConfig,
)
from unstructured.ingest.cli.utils import add_options, conform_click_options
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@dataclass
class BaseDestCmd(BaseCmd):
    def get_dest_runner(self, source_cmd: str, options: dict, parent_options: dict):
        src_cmd_fn = get_src_cmd(cmd_name=source_cmd)
        src_cmd = src_cmd_fn()
        runner = src_cmd.get_source_runner(options=parent_options)
        runner.writer_type = self.cmd_name_key
        runner.writer_kwargs = options
        return runner

    def check_dest_options(self, options: dict):
        self.cli_config.from_dict(options)

    def dest(self, ctx: click.Context, **options):
        if not ctx.parent:
            raise click.ClickException("destination command called without a parent")
        if not ctx.parent.info_name:
            raise click.ClickException("parent command missing info name")
        source_cmd = ctx.parent.info_name.replace("-", "_")
        parent_options: dict = ctx.parent.params if ctx.parent else {}
        conform_click_options(options)
        verbose = parent_options.get("verbose", False)
        ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
        log_options(parent_options, verbose=verbose)
        log_options(options, verbose=verbose)
        try:
            self.check_dest_options(options=options)
            runner = self.get_dest_runner(
                source_cmd=source_cmd,
                options=options,
                parent_options=parent_options,
            )
            runner.run(**parent_options)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e

    def get_dest_cmd(self) -> click.Command:
        # Dynamically create the command without the use of click decorators
        fn = self.dest
        fn = click.pass_context(fn)
        cmd: click.Group = click.command(fn)
        cmd.name = self.cmd_name
        cmd.invoke_without_command = True
        options = [self.cli_config] if self.cli_config else []
        options += self.additional_cli_options
        if self.is_fsspec and CliFilesStorageConfig not in options:
            options.append(CliFilesStorageConfig)
        add_options(cmd, extras=options, is_src=False)
        return cmd
