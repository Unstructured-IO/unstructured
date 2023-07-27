import click

import unstructured.ingest.cli.cmds as cli_cmds
from unstructured.ingest.cli.common import add_shared_options


@click.group()
def ingest():
    pass


subcommands = [
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
    cli_cmds.onedrive,
    cli_cmds.outlook,
    cli_cmds.local,
    cli_cmds.elasticsearch,
    cli_cmds.confluence,
]
# Add all subcommands
for cmd in subcommands:
    add_shared_options(cmd)
    ingest.add_command(cmd)
