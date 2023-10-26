import typing as t

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.cmds import base_src_cmd_fns


def get_src_cmd_map() -> t.Dict[str, t.Callable[[], BaseSrcCmd]]:
    return {b().cmd_name_key: b for b in base_src_cmd_fns}


def get_src_cmd(cmd_name: str) -> t.Callable[[], BaseSrcCmd]:
    return get_src_cmd_map()[cmd_name]
