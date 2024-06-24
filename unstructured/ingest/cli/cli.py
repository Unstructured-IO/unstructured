import click

from unstructured.ingest.cli import dest, src
from unstructured.ingest.v2.cli.cmds import dest as dest_v2
from unstructured.ingest.v2.cli.cmds import src as src_v2


@click.group()
def ingest():
    pass


def get_cmd() -> click.Command:
    """Construct and return a Click command object representing the main command for the CLI.

    This function adds all dest_subcommand(s) to each src_subcommand, and adds all of those
    to the main command as nested subcommands.
    """
    cmd = ingest
    src_dict = {s.name: s for s in src}
    dest_dict = {d.name: d for d in dest}
    for s in src_v2:
        src_dict[s.name] = s
    for d in dest_v2:
        dest_dict[d.name] = d
    # Add all subcommands
    for src_subcommand in src_dict.values():
        # Add all destination subcommands
        for dest_subcommand in dest_dict.values():
            src_subcommand.add_command(dest_subcommand)
        cmd.add_command(src_subcommand)
    return cmd
