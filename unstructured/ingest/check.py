#!/usr/bin/env python3
import logging
from typing import List

import click

from unstructured.ingest.logger import ingest_log_streaming_init, logger


def check_runner(connector: str) -> List[str]:
    import unstructured.ingest.runner as runners

    errors = []
    if not hasattr(runners, connector):
        errors.append(f"'{connector}' does not exist as a submodule in runners modules")
    if connector not in runners.__all__:
        errors.append(
            f"'{connector}' does not listed as an exported module on the "
            f"__all__ list from the runners modules",
        )
    return errors


def check_cli_cmds(connector: str) -> List[str]:
    import unstructured.ingest.cli.cmds as cli_cmds

    errors = []
    if not hasattr(cli_cmds, connector):
        errors.append(f"'{connector}' does not exist as a submodule in cli.cmd modules")
    if connector not in cli_cmds.__all__:
        errors.append(
            f"'{connector}' does not listed as an exported module on the "
            f"__all__ list from the cli.cmd modules",
        )
    return errors


def check_cli(connector: str) -> List[str]:
    from unstructured.ingest.cli.cli import get_cmd

    errors = []
    if connector not in get_cmd().commands.keys():
        errors.append(f"'{connector}' not set as a subcommand on the cli group")
    return errors


@click.command()
@click.argument("connector")
@click.option("-v", "--verbose", is_flag=True, default=False)
def check(connector, verbose):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    logger.info(f"Checking all requirements for connector: {connector}")
    errors = []
    for ch in [check_runner, check_cli_cmds, check_cli]:
        errors.extend(ch(connector=connector))
    if errors:
        for err in errors:
            logger.error(err)
        exit(1)
    logger.info("Checks ran successfully")


if __name__ == "__main__":
    check()
