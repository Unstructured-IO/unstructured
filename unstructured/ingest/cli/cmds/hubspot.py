import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import CliMixin, DelimitedString
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.connector.hubspot import HubSpotObjectTypes
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import HubSpotRunner

OBJECT_TYPES = {t.value for t in HubSpotObjectTypes}


def validate_object_type(ctx, param, value) -> t.List[str]:
    for obj in value:
        if obj not in OBJECT_TYPES:
            raise click.ClickException(
                f"Invalid object type: <{obj}>,\
                            must be one of {OBJECT_TYPES}",
            )
    return value


def validate_custom_property(ctx, param, value) -> t.Dict[str, t.List[str]]:
    output: t.Dict[str, t.List[str]] = {}
    for custom_property in value:
        cprop = custom_property.split(":")
        if len(cprop) < 2:
            logger.warning(f"Wrong custom property format. Omitting: {cprop}")
        elif cprop[0] not in OBJECT_TYPES:
            logger.warning(f"Invalid object type: {cprop[0]}, must be one of {OBJECT_TYPES}")
        else:
            output[cprop[0]] = output.get(cprop[0], []) + [cprop[1]]
    return output


@dataclass
class HubSpotCliConfig(BaseConfig, CliMixin):
    api_token: str
    object_types: t.Optional[t.List[str]] = None
    custom_properties: t.Optional[t.Dict[str, t.List[str]]] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-token"],
                required=True,
                type=str,
                help="Access token to perform operations on Hubspot. \
                    Check \
                    https://developers.hubspot.com/docs/api/private-apps/ \
                    for more info",
            ),
            click.Option(
                ["--object-types"],
                default=None,
                required=False,
                type=DelimitedString(),
                is_flag=False,
                callback=validate_object_type,
                help=f"Object to include in the process.\
                    Must be a subset of {','.join(OBJECT_TYPES)}.\
                    If the argument is omitted all objects listed will be processed.",
            ),
            click.Option(
                ["--custom-properties"],
                default=None,
                required=False,
                type=DelimitedString(),
                is_flag=False,
                callback=validate_custom_property,
                help="Custom property to process information from.\
                    It should be a comma separated list in the form\
                        <object_type>:<custom_property_id>\
                    Must be internal name of the variable. If the property is missing, \
                        it will be omitted.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="hubspot", invoke_without_command=True, cls=Group)
@click.pass_context
def hubspot_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return
    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([HubSpotCliConfig]))
        runner = HubSpotRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = hubspot_source
    add_options(cmd, extras=[HubSpotCliConfig])
    return cmd
