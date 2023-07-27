from __future__ import annotations

import hashlib
import logging
from functools import partial
from pathlib import Path

from click import ClickException, Command, Option

from unstructured.ingest.doc_processor.generalized import process_document
from unstructured.ingest.interfaces import BaseConnector, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.process import Process


def run_init_checks(options: dict):
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    # Initial breaking checks
    if options["local_input_path"] is not None and options["download_dir"]:
        raise ClickException(
            "Files should already be in local file system: there is nothing to download, "
            "but --download-dir is specified.",
        )
    if options["metadata_exclude"] is not None and options["metadata_include"] is not None:
        raise ClickException(
            "Arguments `--metadata-include` and `--metadata-exclude` are "
            "mutually exclusive with each other.",
        )

    # Warnings
    if options["flatten_metadata"] and "metadata" not in options["fields_include"]:
        logger.warning(
            "`--flatten-metadata` is specified, but there is no metadata to flatten, "
            "since `metadata` is not specified in `--fields-include`.",
        )
    if "metadata" not in options["fields_include"] and (
        options["metadata_include"] or options["metadata_exclude"]
    ):
        logger.warning(
            "Either `--metadata-include` or `--metadata-exclude` is specified"
            " while metadata is not specified in --fields-include.",
        )

    if (
        not options["partition_by_api"]
        and options["partition_endpoint"] != "https://api.unstructured.io/general/v0/general"
    ):
        logger.warning(
            "Ignoring --partition-endpoint because --partition-by-api was not set",
        )
    if (not options["preserve_downloads"] and not options["download_only"]) and options[
        "download_dir"
    ]:
        logger.warning(
            "Not preserving downloaded files but --download_dir is specified",
        )


def log_options(options: dict):
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    sensitive_fields = [
        "account_name",
        "account_key",
        "api_key",
        "token",
        "client_id",
        "client_cred",
    ]
    options_to_log = options.copy()
    options_to_log.update(
        {
            k: "*******"
            for k, v in options_to_log.items()
            if k in sensitive_fields and v is not None
        },
    )
    logger.debug(f"options: {options_to_log}")


def map_to_standard_config(options: dict) -> StandardConnectorConfig:
    return StandardConnectorConfig(
        download_dir=options["download_dir"],
        output_dir=options["structured_output_dir"],
        download_only=options["download_only"],
        fields_include=options["fields_include"],
        flatten_metadata=options["flatten_metadata"],
        metadata_exclude=options["metadata_exclude"],
        metadata_include=options["metadata_include"],
        partition_by_api=options["partition_by_api"],
        partition_endpoint=options["partition_endpoint"],
        preserve_downloads=options["preserve_downloads"],
        re_download=options["re_download"],
        api_key=options["api_key"],
    )


def update_download_dir_remote_url(options: dict, remote_url: str, logger: logging.Logger) -> None:
    hashed_dir_name = hashlib.sha256(remote_url.encode("utf-8"))
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)


def update_download_dir_hash(
    options: dict,
    hashed_dir_name: hashlib._Hash,
    logger: logging.Logger,
):
    if options["local_input_path"] is None and not options["download_dir"]:
        cache_path = Path.home() / ".cache" / "unstructured" / "ingest"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
        download_dir = cache_path / hashed_dir_name.hexdigest()[:10]
        if options["preserve_downloads"]:
            logger.warning(
                f"Preserving downloaded files but --download-dir is not specified,"
                f" using {download_dir}",
            )
        options["download_dir"] = download_dir


def process_documents(doc_connector: BaseConnector, options: dict) -> None:
    process_document_with_partition_args = partial(
        process_document,
        strategy=options["partition_strategy"],
        ocr_languages=options["partition_ocr_languages"],
        encoding=options["encoding"],
    )

    Process(
        doc_connector=doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=options["num_processes"],
        reprocess=options["reprocess"],
        verbose=options["verbose"],
        max_docs=options["max_docs"],
    ).run()


def add_shared_options(cmd: Command):
    options = [
        Option(
            ["--max-docs"],
            default=None,
            type=int,
            help="If specified, process at most specified number of documents.",
        ),
        Option(
            ["--flatten-metadata"],
            is_flag=True,
            default=False,
            help="Results in flattened json elements. "
            "Specifically, the metadata key values are brought to the top-level of the element, "
            "and the `metadata` key itself is removed.",
        ),
        Option(
            ["--fields-include"],
            default="element_id,text,type,metadata",
            help="If set, include the specified top-level fields in an element. "
            "Default is `element_id,text,type,metadata`.",
        ),
        Option(
            ["--metadata-include"],
            default=None,
            help="If set, include the specified metadata fields if they exist "
            "and drop all other fields. "
            "Usage: provide a single string with comma separated values. "
            "Example: --metadata-include filename,page_number ",
        ),
        Option(
            ["--metadata-exclude"],
            default=None,
            help="If set, drop the specified metadata fields if they exist. "
            "Usage: provide a single string with comma separated values. "
            "Example: --metadata-exclude filename,page_number ",
        ),
        Option(
            ["--partition-by-api"],
            is_flag=True,
            default=False,
            help="Use a remote API to partition the files."
            " Otherwise, use the function from partition.auto",
        ),
        Option(
            ["--partition-endpoint"],
            default="https://api.unstructured.io/general/v0/general",
            help="If partitioning via api, use the following host. "
            "Default: https://api.unstructured.io/general/v0/general",
        ),
        Option(
            ["--partition-strategy"],
            default="auto",
            help="The method that will be used to process the documents. "
            "Default: auto. Other strategies include `fast` and `hi_res`.",
        ),
        Option(
            ["--partition-ocr-languages"],
            default="eng",
            help="A list of language packs to specify which languages to use for OCR, "
            "separated by '+' e.g. 'eng+deu' to use the English and German language packs. "
            "The appropriate Tesseract "
            "language pack needs to be installed."
            "Default: eng",
        ),
        Option(
            ["--encoding"],
            default="utf-8",
            help="Text encoding to use when reading documents. Default: utf-8",
        ),
        Option(
            ["--api-key"],
            default="",
            help="API Key for partition endpoint.",
        ),
        Option(
            ["--local-input-path"],
            default=None,
            help="Path to the location in the local file system that will be processed.",
        ),
        Option(
            ["--local-file-glob"],
            default=None,
            help="A comma-separated list of file globs to limit which "
            "types of local files are accepted,"
            " e.g. '*.html,*.txt'",
        ),
        Option(
            ["--download-dir"],
            help="Where files are downloaded to, defaults to "
            "`$HOME/.cache/unstructured/ingest/<SHA256>`.",
        ),
        Option(
            ["--preserve-downloads"],
            is_flag=True,
            default=False,
            help="Preserve downloaded files. Otherwise each file is removed after being processed "
            "successfully.",
        ),
        Option(
            ["--download-only"],
            is_flag=True,
            default=False,
            help="Download any files that are not already present in either --download-dir or "
            "the default download ~/.cache/... location in case --download-dir "
            "is not specified and "
            "skip processing them through unstructured.",
        ),
        Option(
            ["--re-download/--no-re-download"],
            default=False,
            help="Re-download files even if they are already present in --download-dir.",
        ),
        Option(
            ["--structured-output-dir"],
            default="structured-output",
            help="Where to place structured output .json files.",
        ),
        Option(
            ["--reprocess"],
            is_flag=True,
            default=False,
            help="Reprocess a downloaded file even if the relevant structured output .json file "
            "in --structured-output-dir already exists.",
        ),
        Option(
            ["--num-processes"],
            default=2,
            show_default=True,
            help="Number of parallel processes to process docs in.",
        ),
        Option(["-v", "--verbose"], is_flag=True, default=False),
    ]
    cmd.params.extend(options)
