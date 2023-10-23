import collections
import typing as t

from unstructured.ingest.cli.cmds import base_src_cmd_fns


def get_src_cmd_map() -> t.Dict[str, t.Callable]:
    # Make sure there are not overlapping names
    cmd_names = [b().cmd_name for b in base_src_cmd_fns]
    duplicates = [item for item, count in collections.Counter(cmd_names).items() if count > 1]
    if len(cmd_names) != len(list(set(cmd_names))):
        raise ValueError(
            "multiple base commands defined with the same names: {}".format(", ".join(duplicates)),
        )
    return {b().cmd_name: b for b in base_src_cmd_fns}


def get_src_cmd(cmd_name: str) -> t.Callable:
    return get_src_cmd_map()[cmd_name]
