import json

import click
import jsonschema

from unstructured.ingest.cli.cmds.notion_pkg.partition import get_cmd


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
def partition_spec(schema: bool, generate_cli_skeleton: bool, validate_json):
    _, configs = get_cmd()
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
