import hashlib
import logging
from functools import partial
from pathlib import Path

import click

from unstructured.ingest.doc_processor.generalized import process_document
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.process import Process


@click.command()
@click.pass_context
@click.option(
    "--anonymous",
    is_flag=True,
    default=False,
    help="Connect to s3 without local AWS credentials.",
)
@click.option(
    "--remote-url",
    required=True,
    help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
    "a directory or a single file. Supported protocols are: `s3`, `s3a`",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `s3`, `s3a`",
)
def s3(ctx, anonymous, remote_url, recursive):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "anonymous": anonymous,
                "remote_url": remote_url,
                "recursive": recursive,
            },
        ),
    )

    if context_dict["local_input_path"] is None and not context_dict["download_dir"]:
        cache_path = Path.home() / ".cache" / "unstructured" / "ingest"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
        hashed_dir_name = hashlib.sha256(remote_url.encode("utf-8"))
        download_dir = cache_path / hashed_dir_name.hexdigest()[:10]
        if context_dict["preserve_downloads"]:
            logger.warning(
                f"Preserving downloaded files but --download-dir is not specified,"
                f" using {download_dir}",
            )
        context_dict["download_dir"] = download_dir

    from unstructured.ingest.cli.common import map_to_standard_config
    from unstructured.ingest.connector.s3 import S3Connector, SimpleS3Config

    doc_connector = S3Connector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleS3Config(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"anon": anonymous},
        ),
    )

    process_document_with_partition_args = partial(
        process_document,
        strategy=context_dict["partition_strategy"],
        ocr_languages=context_dict["partition_ocr_languages"],
        encoding=context_dict["encoding"],
    )

    Process(
        doc_connector=doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=context_dict["num_processes"],
        reprocess=context_dict["reprocess"],
        verbose=context_dict["verbose"],
        max_docs=context_dict["max_docs"],
    ).run()
