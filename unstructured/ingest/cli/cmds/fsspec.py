from unstructured.ingest.cli.cmds.base_cmd import BaseCmd


def get_base_cmd() -> BaseCmd:
    cmd_cls = BaseCmd(cmd_name="fsspec", is_fsspec=True)
    return cmd_cls
