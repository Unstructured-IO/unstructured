import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import SalesforceRunner


@dataclass
class SalesforceCliConfig(BaseConfig, CliMixin):
    username: str
    consumer_key: str
    private_key_path: str
    categories: t.List[str]

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        possible_categories = ["Account", "Case", "Campaign", "EmailMessage", "Lead"]
        options = [
            click.Option(
                ["--username"],
                required=True,
                type=str,
                help="Salesforce username usually looks like an email.",
            ),
            click.Option(
                ["--consumer-key"],
                required=True,
                type=str,
                help="For the Salesforce JWT auth. Found in Consumer Details.",
            ),
            click.Option(
                ["--private-key-path"],
                required=True,
                type=click.Path(file_okay=True, exists=True, dir_okay=False),
                help="Path to the private key for the Salesforce JWT auth. "
                "Usually named server.key.",
            ),
            click.Option(
                ["--categories"],
                default=None,
                required=True,
                type=DelimitedString(choices=possible_categories),
                help="Comma-delimited salesforce categories to download. "
                "Currently only {}.".format(", ".join(possible_categories)),
            ),
        ]
        return options


@click.group(name="salesforce", invoke_without_command=True, cls=Group)
@click.pass_context
def salesforce_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([SalesforceCliConfig]))
        runner = SalesforceRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = salesforce_source
    add_options(cmd, extras=[SalesforceCliConfig, CliRecursiveConfig])
    return cmd
