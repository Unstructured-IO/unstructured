import click

from unstructured.ingest.v2.cli.cmds import dest, src


@click.group()
def ingest():
    pass


def get_cmd() -> click.Command:
    """Construct and return a Click command object representing the main command for the CLI.

    This function adds all dest_subcommand(s) to each src_subcommand, and adds all of those
    to the main command as nested subcommands.
    """
    cmd = ingest
    # Add all subcommands
    for src_subcommand in src:
        # Add all destination subcommands
        for dest_subcommand in dest:
            src_subcommand.add_command(dest_subcommand)
        cmd.add_command(src_subcommand)
    return cmd
