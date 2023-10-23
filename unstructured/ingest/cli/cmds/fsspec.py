from unstructured.ingest.cli.base.src import BaseSrcCmd


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="fsspec", is_fsspec=True)
    return cmd_cls
