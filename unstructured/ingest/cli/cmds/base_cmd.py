import logging
import typing as t
from dataclasses import dataclass, field

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import CliFilesStorageConfig, CliMixin
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig, FsspecConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import runner_map


@dataclass
class BaseCmd:
    cmd_name: str
    cli_config: t.Optional[t.Type[BaseConfig]] = None
    additional_cli_options: t.List[t.Type[CliMixin]] = field(default_factory=list)
    addition_configs: t.Dict[str, t.Type[BaseConfig]] = field(default_factory=dict)
    is_fsspec: bool = False

    def get_source_runner(self, **options):
        addition_configs = self.addition_configs
        if self.is_fsspec and "fsspec_config" not in addition_configs:
            addition_configs["fsspec_config"] = FsspecConfig
        configs = extract_configs(
            options,
            validate=[self.cli_config] if self.cli_config else None,
            extras=addition_configs,
        )
        runner = runner_map[self.cmd_name]
        return runner(**configs)  # type: ignore

    def src(self, ctx: click.Context, **options):
        if ctx.invoked_subcommand:
            return

        conform_click_options(options)
        verbose = options.get("verbose", False)
        ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
        log_options(options, verbose=verbose)
        try:
            runner = self.get_source_runner(**options)
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

    def get_dest_cmd(self) -> t.Optional[click.Command]:
        return None
