import logging
from typing import Optional

from click import ClickException, Command, Option

from unstructured.ingest.interfaces import (
    ProcessorConfigs,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


def run_init_checks(
    verbose: bool,
    local_input_path: Optional[str],
    download_dir: Optional[str],
    metadata_exclude: Optional[str],
    metadata_include: Optional[str],
    flatten_metadata: bool,
    fields_include: str,
    partition_by_api: bool,
    partition_endpoint: Optional[str],
    preserve_downloads: bool,
    download_only: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    # Initial breaking checks
    if local_input_path is not None and download_dir:
        raise ClickException(
            "Files should already be in local file system: there is nothing to download, "
            "but --download-dir is specified.",
        )
    if metadata_exclude is not None and metadata_include is not None:
        raise ClickException(
            "Arguments `--metadata-include` and `--metadata-exclude` are "
            "mutually exclusive with each other.",
        )

    # Warnings
    if flatten_metadata and "metadata" not in fields_include:
        logger.warning(
            "`--flatten-metadata` is specified, but there is no metadata to flatten, "
            "since `--metadata` is not specified in `--fields-include`.",
        )
    if "metadata" not in fields_include and (metadata_include or metadata_exclude):
        logger.warning(
            "Either '--metadata-include` or `--metadata-exclude` is specified"
            " while metadata is not specified in fields-include.",
        )

    if (
        not partition_by_api
        and partition_endpoint != "https://api.unstructured.io/general/v0/general"
    ):
        logger.warning(
            "Ignoring --partition-endpoint because --partition-by-api was not set",
        )
    if (not preserve_downloads and not download_only) and download_dir:
        logger.warning(
            "Not preserving downloaded files but download_dir is specified",
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


def map_to_processor_config(options: dict) -> ProcessorConfigs:
    return ProcessorConfigs(
        partition_strategy=options["partition_strategy"],
        partition_ocr_languages=options["partition_ocr_languages"],
        partition_pdf_infer_table_structure=options["partition_pdf_infer_table_structure"],
        partition_encoding=options["partition_encoding"],
        num_processes=options["num_processes"],
        reprocess=options["reprocess"],
        max_docs=options["max_docs"],
    )


def add_remote_url_option(cmd: Command):
    cmd.params.append(
        Option(
            ["--remote-url"],
            required=True,
            help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
            "a directory or a single file.",
        ),
    )


def add_recursive_option(cmd: Command):
    cmd.params.append(
        Option(
            ["--recursive"],
            is_flag=True,
            default=False,
            help="Recursively download files in their respective folders"
            "otherwise stop at the files in provided folder level.",
        ),
    )


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
            ["--partition-pdf-infer-table-structure"],
            default=False,
            help="If set to True, partition will includ the table's text content in the response."
            "Default: False",
        ),
        Option(
            ["--partition-encoding"],
            default=None,
            help="Text encoding to use when reading documents. By default the encoding is "
            "detected automatically.",
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
