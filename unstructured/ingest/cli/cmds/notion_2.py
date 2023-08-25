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
from unstructured.ingest.runner.notion import read as notion_fn_read


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


@click.group
def notion():
    pass


@click.command
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
        _, configs = get_read_cmd()
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


@click.command()
@click.option("--schema", is_flag=True, help="show expected schema of input json for read command")
@click.option(
    "--generate-cli-skeleton",
    is_flag=True,
    help="generate sample json skeleton for read input",
)
@click.option(
    "--validate-json",
    type=click.File("rb"),
    help="given a json file, validate it against expected schema",
)
def read_spec(schema: bool, generate_cli_skeleton: bool, validate_json):
    _, configs = get_read_cmd()
    if len(configs) == 0:
        return
    base = configs.pop(0)

    if schema:
        click.echo(json.dumps(base.merge_schemas(configs=configs), indent=3))
        exit()
    if generate_cli_skeleton:
        click.echo(json.dumps(base.merge_sample_jsons(configs=configs), indent=3))
        exit()
    if validate_json:
        try:
            data = json.load(validate_json)
        except json.decoder.JSONDecodeError:
            raise click.ClickException("input file not valid json")
        try:
            jsonschema.validate(data, schema=base.merge_schemas(configs=configs))
        except jsonschema.ValidationError as error:
            raise click.ClickException(f"input json not valid: {error}")


def get_read_cmd() -> Tuple[click.Command, List[Type[BaseConfig]]]:
    cmd = read
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


def get_group() -> click.Group:
    parent = notion
    parent.add_command(read_spec)
    read_cmd, _ = get_read_cmd()
    parent.add_command(read_cmd)

    return parent
