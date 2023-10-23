import typing as t

from unstructured.ingest.cli.cmds import base_src_cmd_fns


def get_src_cmd_map() -> t.Dict[str, t.Callable]:
    return {b().cmd_name: b for b in base_src_cmd_fns}


def get_src_cmd(cmd_name: str) -> t.Callable:
    return get_src_cmd_map()[cmd_name]
