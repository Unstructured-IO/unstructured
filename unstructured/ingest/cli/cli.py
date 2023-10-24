import click

from unstructured.ingest.cli import dest, src


@click.group()
def ingest():
    pass


def get_cmd() -> click.Command:
    cmd = ingest
    # Add all subcommands
    for src_subcommand in src:
        # add destination subcommands
        for dest_subcommand in dest:
            src_subcommand.add_command(dest_subcommand)
        cmd.add_command(src_subcommand)
    return cmd
