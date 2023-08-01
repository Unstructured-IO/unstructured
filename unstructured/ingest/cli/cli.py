import click

import unstructured.ingest.cli.cmds as cli_cmds


@click.group()
def ingest():
    pass


# Dynamically update shared options for supported subcommands
for subcommand_name in cli_cmds.__all__:
    subcommand = getattr(cli_cmds, subcommand_name)
    ingest.add_command(subcommand())


def get_cmd() -> click.Command:
    return ingest