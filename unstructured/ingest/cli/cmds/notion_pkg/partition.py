import json
import logging
from typing import List, Tuple, Type

import click
import jsonschema

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.interfaces import BaseConfig, PartitionConfigs
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
def partition(**options):
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)

    cli_input_json = options.pop("cli_input_json", None)
    if cli_input_json:
        data: dict = json.load(cli_input_json)
        _, configs = get_cmd()
        base = configs.pop(0)
        jsonschema.validate(data, schema=base.merge_schemas(configs=configs))
        for k, v in data.items():
            if not options.get(k, None):
                options[k] = v

    logger.info(f"updated values: {options}")
    partition_configs = PartitionConfigs.from_dict(options)
    for k in partition_configs.__dict__:
        options.pop(k, None)
    # TODO add partition code


def get_cmd() -> Tuple[click.Command, List[Type[BaseConfig]]]:
    cmd: click.Command = partition
    PartitionConfigs.add_cli_options(cmd)
    cmd.params.append(
        click.Option(
            ["--cli-input-json"],
            type=click.File("rb"),
            help="optional json to pass in to populate expected cli params",
        ),
    )
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd, [PartitionConfigs]
