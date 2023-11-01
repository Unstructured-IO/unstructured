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
from unstructured.ingest.interfaces import BaseConfig, DatabricksVolumesConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@dataclass
class DatabricksSrcCmd(BaseSrcCmd):
    cli_config: t.Optional[t.Type[BaseConfig]] = CliFilesStorageConfig
    auth_cli_config: t.Optional[t.Type[BaseConfig]] = None

    def __post_init__(self):
        # Due to python3.8 limitation, required fields can't be added in children dataclasses
        if self.auth_cli_config is None:
            raise ValueError("auth_cli_config required")
        self.additional_cli_options.append(self.auth_cli_config)
        self.addition_configs["databricks_volume_config"] = DatabricksVolumesConfig

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
        auth_configs = self.auth_cli_config.from_dict(options)
        try:
            runner = self.get_source_runner(options=options)
            runner.run(auth_configs=auth_configs, **options)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise click.ClickException(str(e)) from e
