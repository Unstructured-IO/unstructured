import logging
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.cmd import BaseCmd
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import CliFilesStorageConfig
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import runner_map


@dataclass
class BaseSrcCmd(BaseCmd):
    def get_source_runner(self, options: dict):
        addition_configs = self.addition_configs
        if "connector_config" not in addition_configs:
            addition_configs["connector_config"] = self.cli_config
        configs = extract_configs(
            options,
            validate=[self.cli_config] if self.cli_config else None,
            extras=addition_configs,
        )
        runner = runner_map[self.cmd_name_key]
        return runner(**configs)  # type: ignore

    def src(self, ctx: click.Context, **options):
        if ctx.invoked_subcommand:
            return

        conform_click_options(options)
        verbose = options.get("verbose", False)
        ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
        log_options(options, verbose=verbose)
        try:
            runner = self.get_source_runner(options=options)
            runner.run(**options)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e

    def get_src_cmd(self) -> click.Group:
        # Dynamically create the command without the use of click decorators
        fn = self.src
        fn = click.pass_context(fn)
        cmd: click.Group = click.group(fn, cls=Group)
        cmd.name = self.cmd_name
        cmd.invoke_without_command = True
        extra_options = [self.cli_config] if self.cli_config else []
        extra_options += self.additional_cli_options
        if self.is_fsspec and CliFilesStorageConfig not in extra_options:
            extra_options.append(CliFilesStorageConfig)
        add_options(cmd, extras=extra_options)
        return cmd
