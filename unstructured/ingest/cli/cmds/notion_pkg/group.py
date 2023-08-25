import click

from unstructured.ingest.cli.cmds.notion_pkg.partition import (
    get_cmd as get_partition_cmd,
)
from unstructured.ingest.cli.cmds.notion_pkg.partition_spec import partition_spec
from unstructured.ingest.cli.cmds.notion_pkg.read import get_cmd as get_read_cmd
from unstructured.ingest.cli.cmds.notion_pkg.read_spec import read_spec


@click.group()
def notion():
    pass


def get_group() -> click.Group:
    parent: click.Group = notion
    parent.add_command(read_spec)
    read_cmd, _ = get_read_cmd()
    parent.add_command(read_cmd)
    partition_cmd, _ = get_partition_cmd()
    parent.add_command(partition_cmd)
    parent.add_command(partition_spec)
    return parent
