import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import (
    DelimitedString,
    Group,
    conform_click_options,
)
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import salesforce as salesforce_fn


@dataclass
class SalesforceCliConfig(BaseConfig, CliMixin):
    username: str
    consumer_key: str
    private_key_path: str
    categories: t.List[str]

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        SalesforceCliConfig.from_dict(options)
        salesforce_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = salesforce_source
    SalesforceCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
