import click

import unstructured.ingest.cli.cmds as cli_cmds


@click.group()
def ingest():
    pass


# Dynamically update shared options for supported subcommands
subcommands = [
    cli_cmds.box,
    cli_cmds.s3,
    cli_cmds.gcs,
    cli_cmds.dropbox,
    cli_cmds.azure,
    cli_cmds.fsspec,
    cli_cmds.github,
    cli_cmds.gitlab,
    cli_cmds.reddit,
    cli_cmds.slack,
    cli_cmds.discord,
    cli_cmds.wikipedia,
    cli_cmds.gdrive,
    cli_cmds.biomed,
    cli_cmds.notion,
    cli_cmds.onedrive,
    cli_cmds.outlook,
    cli_cmds.local,
    cli_cmds.elasticsearch,
    cli_cmds.confluence,
    cli_cmds.sharepoint,
]

for subcommand in subcommands:
    ingest.add_command(subcommand())


def get_cmd() -> click.Command:
    cmd = ingest
    # Add all subcommands
    for subcommand in subcommands:
        # add_shared_options(cmd)
        cmd.add_command(subcommand())
    return cmd
