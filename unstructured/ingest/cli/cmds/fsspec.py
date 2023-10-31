from unstructured.ingest.cli.base.src import BaseSrcCmd

CMD_NAME = "fsspec"


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name=CMD_NAME, is_fsspec=True)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(cmd_name=CMD_NAME, is_fsspec=True)
    return cmd_cls
