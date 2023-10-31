import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import CliFilesStorageConfig
from unstructured.ingest.cli.utils import conform_click_options
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@dataclass
class DatabricksSrcCmd(BaseSrcCmd):
    cli_config: t.Optional[t.Type[BaseConfig]] = CliFilesStorageConfig

    @property
    def cmd_name_key(self):
        return "databricks_volumes"

    def src(self, ctx: click.Context, **options):
        if ctx.invoked_subcommand:
            return

        conform_click_options(options)
        verbose = options.get("verbose", False)
        ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
        log_options(options, verbose=verbose)
        auth_cli_config = self.additional_cli_options[0]
        auth_configs = auth_cli_config.from_dict(options)
        try:
            runner = self.get_source_runner(options=options)
            runner.run(auth_configs=auth_configs, **options)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e
