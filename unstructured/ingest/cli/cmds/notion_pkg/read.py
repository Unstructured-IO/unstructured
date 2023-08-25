import json
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Type

import click
import jsonschema

from unstructured.ingest.cli.common import (
    RecursiveOption,
    log_options,
)
from unstructured.ingest.interfaces import BaseConfig, ReadConfigs
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.notion_pkg import read as notion_fn_read


@dataclass
class NotionReadConfig(BaseConfig):
    api_key: str
    page_ids: List[str] = field(default_factory=list)
    database_ids: List[str] = field(default_factory=list)

    @classmethod
    def get_sample_dict(cls) -> dict:
        config = cls(api_key="to populate")
        return config.__dict__

    @staticmethod
    def get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": ["string", "null"], "default": None},
                "page_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "database_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
            },
        }

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--page-ids"],
                default=None,
                multiple=True,
                help="List of Notion page IDs to pull text from",
            ),
            click.Option(
                ["--database-ids"],
                default=None,
                multiple=True,
                help="List of Notion database IDs to pull text from",
            ),
            click.Option(
                ["--api-key"],
                # required=True,
                help="API key for Notion api",
            ),
        ]
        cmd.params.extend(options)


@click.command()
def read(**options):
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
    read_configs = ReadConfigs.from_dict(options)
    notion_configs = NotionReadConfig.from_dict(options)
    for k in read_configs.__dict__:
        options.pop(k, None)
    for k in notion_configs.__dict__:
        options.pop(k, None)
    try:
        notion_fn_read(read_configs=read_configs, **notion_configs.__dict__, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> Tuple[click.Command, List[Type[BaseConfig]]]:
    cmd: click.Command = read
    ReadConfigs.add_cli_options(cmd)
    NotionReadConfig.add_cli_options(cmd)
    RecursiveOption.add_cli_options(cmd)
    cmd.params.append(
        click.Option(
            ["--cli-input-json"],
            type=click.File("rb"),
            help="optional json to pass in to populate expected cli params",
        ),
    )
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd, [ReadConfigs, NotionReadConfig, RecursiveOption]
