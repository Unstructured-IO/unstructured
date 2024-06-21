import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliMixin, DelimitedString, Dict
from unstructured.ingest.connector.hubspot import HubSpotObjectTypes, SimpleHubSpotConfig

OBJECT_TYPES = {t.value for t in HubSpotObjectTypes}


def validate_custom_property(ctx, param, value) -> t.Dict[str, t.List[str]]:
    if not value:
        return value
    for k in value:
        if k not in OBJECT_TYPES:
            raise ValueError(f"Invalid object type: {k}, must be one of {OBJECT_TYPES}")
        if not isinstance(value[k], list):
            raise ValueError(f"Invalid type: {type(value[k])}, must be a Python list.")
    return value


@dataclass
class HubSpotCliConfig(SimpleHubSpotConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
                type=DelimitedString(choices=OBJECT_TYPES),
                is_flag=False,
                help=f"Object to include in the process.\
                    Must be a subset of {','.join(OBJECT_TYPES)}.\
                    If the argument is omitted all objects listed will be processed.",
            ),
            click.Option(
                ["--custom-properties"],
                default=None,
                required=False,
                type=Dict(),
                is_flag=False,
                callback=validate_custom_property,
                help="Custom property to process information from.\
                    It should be a json-like string in the form\
                        <object_type>:[<custom_property_id>, ..., <custom_property_id>]\
                    Must be internal name of the variable. If the property is missing, \
                        it will be omitted.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="hubspot",
        cli_config=HubSpotCliConfig,
    )
    return cmd_cls
