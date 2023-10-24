import typing as t

import click

from unstructured.ingest.cli.cmds import base_dest_cmd_fns, base_src_cmd_fns

src: t.List[click.Group] = [v().get_src_cmd() for v in base_src_cmd_fns]

dest: t.List[click.Command] = [v().get_dest_cmd() for v in base_dest_cmd_fns]

__all__ = [
    "src",
    "dest",
]
