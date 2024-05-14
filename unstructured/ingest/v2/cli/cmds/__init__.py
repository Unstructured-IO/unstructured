import click

from .fsspec.s3 import s3_dest_cmd, s3_src_cmd
from .local import local_dest_cmd, local_src_cmd

src: list[click.Group] = [v.get_cmd() for v in [local_src_cmd, s3_src_cmd]]

dest: list[click.Command] = [v.get_cmd() for v in [local_dest_cmd, s3_dest_cmd]]
