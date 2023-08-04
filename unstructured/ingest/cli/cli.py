import click

import unstructured.ingest.cli.cmds as cli_cmds


@click.group()
def ingest():
    pass


def get_cmd() -> click.Command:
    cmd = ingest
    # Add all subcommands
    for subcommand in cli_cmds.__all__:
        sub = getattr(cli_cmds, subcommand)
        cmd.add_command(sub())
    return cmd
