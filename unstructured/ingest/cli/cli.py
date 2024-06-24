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
    # TODO Remove custom logic around v2 connectors once all connectors migrated:
    #  Inject the v2 connectors to override the existing v1 connectors
    #  If a v2 source connector is used, only a v2 destination connector can be associated
    # Add all subcommands
    for src_key, src_subcommand in src_dict.items():
        # Add all destination subcommands
        if src_key in [s.name for s in src_v2]:
            for dest_subcommand in dest_v2:
                src_subcommand.add_command(dest_subcommand)
        else:
            for dest_subcommand in dest_dict.values():
                src_subcommand.add_command(dest_subcommand)
        cmd.add_command(src_subcommand)
    return cmd
