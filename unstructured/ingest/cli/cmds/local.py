import logging

import click

from unstructured.ingest.cli.common import (
    map_to_standard_config,
    process_documents,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.pass_context
@click.option(
    "--input-path",
    required=True,
    help="Path to the location in the local file system that will be processed.",
)
@click.option(
    "--file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of local files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level.",
)
def local(
    ctx,
    input_path,
    file_glob,
    recursive,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "input_path": input_path,
                "file_glob": file_glob,
                "recursive": recursive,
            },
        ),
    )

    from unstructured.ingest.connector.local import (
        LocalConnector,
        SimpleLocalConfig,
    )

    doc_connector = LocalConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleLocalConfig(
            input_path=input_path,
            recursive=recursive,
            file_glob=file_glob,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
