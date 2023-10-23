import click

import unstructured.ingest.cli.cmds as cli_cmds


@click.group()
def ingest():
    pass


def get_cmd() -> click.Command:
    cmd = ingest
    # Add all subcommands
    for src_subcommand in cli_cmds.src:
        # add destination subcommands
        for dest_subcommand in cli_cmds.dest:
            src_subcommand.add_command(dest_subcommand)
        cmd.add_command(src_subcommand)
    return cmd
