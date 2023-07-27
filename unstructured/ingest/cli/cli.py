import click

import unstructured.ingest.cli.cmds as cli_cmds
from unstructured.ingest.cli.common import add_shared_options


@click.group()
def ingest():
    pass


# Dynamically update shared options for supported subcommands
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

remote_url_commands = [cli_cmds.azure, cli_cmds.dropbox, cli_cmds.fsspec, cli_cmds.gcs, cli_cmds.s3]
for cmd in remote_url_commands:
    cmd.params.append(
        click.Option(
            ["--remote-url"],
            required=True,
            help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
            "a directory or a single file.",
        ),
    )

recursive_commands = [
    cli_cmds.azure,
    cli_cmds.dropbox,
    cli_cmds.fsspec,
    cli_cmds.gcs,
    cli_cmds.gdrive,
    cli_cmds.local,
    cli_cmds.onedrive,
    cli_cmds.outlook,
    cli_cmds.s3,
]
for cmd in recursive_commands:
    cmd.params.append(
        click.Option(
            ["--recursive"],
            is_flag=True,
            default=False,
            help="Recursively download files in their respective folders"
            "otherwise stop at the files in provided folder level.",
        ),
    )

# Add all subcommands
for cmd in subcommands:
    add_shared_options(cmd)
    ingest.add_command(cmd)
