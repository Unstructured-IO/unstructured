import logging

import click
from click import ClickException

import unstructured.ingest.cli.cmds as cli_cmds
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.group()
@click.pass_context
@click.option(
    "--max-docs",
    default=None,
    type=int,
    help="If specified, process at most specified number of documents.",
)
@click.option(
    "--flatten-metadata",
    is_flag=True,
    default=False,
    help="Results in flattened json elements. "
    "Specifically, the metadata key values are brought to the top-level of the element, "
    "and the `metadata` key itself is removed.",
)
@click.option(
    "--fields-include",
    default="element_id,text,type,metadata",
    help="If set, include the specified top-level fields in an element. "
    "Default is `element_id,text,type,metadata`.",
)
@click.option(
    "--metadata-include",
    default=None,
    help="If set, include the specified metadata fields if they exist and drop all other fields. "
    "Usage: provide a single string with comma separated values. "
    "Example: --metadata-include filename,page_number ",
)
@click.option(
    "--metadata-exclude",
    default=None,
    help="If set, drop the specified metadata fields if they exist. "
    "Usage: provide a single string with comma separated values. "
    "Example: --metadata-exclude filename,page_number ",
)
@click.option(
    "--partition-by-api",
    is_flag=True,
    default=False,
    help="Use a remote API to partition the files."
    " Otherwise, use the function from partition.auto",
)
@click.option(
    "--partition-endpoint",
    default="https://api.unstructured.io/general/v0/general",
    help="If partitioning via api, use the following host. "
    "Default: https://api.unstructured.io/general/v0/general",
)
@click.option(
    "--partition-strategy",
    default="auto",
    help="The method that will be used to process the documents. "
    "Default: auto. Other strategies include `fast` and `hi_res`.",
)
@click.option(
    "--partition-ocr-languages",
    default="eng",
    help="A list of language packs to specify which languages to use for OCR, separated by '+' "
    "e.g. 'eng+deu' to use the English and German language packs. The appropriate Tesseract "
    "language pack needs to be installed."
    "Default: eng",
)
@click.option(
    "--encoding",
    default="utf-8",
    help="Text encoding to use when reading documents. Default: utf-8",
)
@click.option(
    "--api-key",
    default="",
    help="API Key for partition endpoint.",
)
@click.option(
    "--local-input-path",
    default=None,
    help="Path to the location in the local file system that will be processed.",
)
@click.option(
    "--local-file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of local files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--download-dir",
    help="Where files are downloaded to, defaults to `$HOME/.cache/unstructured/ingest/<SHA256>`.",
)
@click.option(
    "--preserve-downloads",
    is_flag=True,
    default=False,
    help="Preserve downloaded files. Otherwise each file is removed after being processed "
    "successfully.",
)
@click.option(
    "--download-only",
    is_flag=True,
    default=False,
    help="Download any files that are not already present in either --download-dir or "
    "the default download ~/.cache/... location in case --download-dir is not specified and "
    "skip processing them through unstructured.",
)
@click.option(
    "--re-download/--no-re-download",
    default=False,
    help="Re-download files even if they are already present in --download-dir.",
)
@click.option(
    "--structured-output-dir",
    default="structured-output",
    help="Where to place structured output .json files.",
)
@click.option(
    "--reprocess",
    is_flag=True,
    default=False,
    help="Reprocess a downloaded file even if the relevant structured output .json file "
    "in --structured-output-dir already exists.",
)
@click.option(
    "--num-processes",
    default=2,
    show_default=True,
    help="Number of parallel processes to process docs in.",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
def ingest(
    ctx,
    max_docs,
    flatten_metadata,
    fields_include,
    metadata_include,
    metadata_exclude,
    partition_by_api,
    partition_endpoint,
    partition_strategy,
    partition_ocr_languages,
    encoding,
    api_key,
    local_input_path,
    local_file_glob,
    download_dir,
    preserve_downloads,
    download_only,
    re_download,
    structured_output_dir,
    reprocess,
    num_processes,
    verbose,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    # Initial braeking checks
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
            "since `metadata` is not specified in `--fields-include`.",
        )
    if "metadata" not in fields_include and (metadata_include or metadata_exclude):
        logger.warning(
            "Either `--metadata-include` or `--metadata-exclude` is specified"
            " while metadata is not specified in --fields-include.",
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
            "Not preserving downloaded files but --download_dir is specified",
        )

    ctx.ensure_object(dict)

    ctx_dict: dict = ctx.obj

    # make sure all parent inputs are available for child subcommands
    ctx_dict.update(
        {
            "verbose": verbose,
            "max_docs": max_docs,
            "flatten_metadata": flatten_metadata,
            "fields_include": fields_include,
            "metadata_include": metadata_include,
            "metadata_exclude": metadata_exclude,
            "partition_by_api": partition_by_api,
            "partition_endpoint": partition_endpoint,
            "partition_strategy": partition_strategy,
            "partition_ocr_languages": partition_ocr_languages,
            "encoding": encoding,
            "api_key": api_key,
            "local_input_path": local_input_path,
            "local_file_glob": local_file_glob,
            "download_dir": download_dir,
            "preserve_downloads": preserve_downloads,
            "download_only": download_only,
            "re_download": re_download,
            "structured_output_dir": structured_output_dir,
            "reprocess": reprocess,
            "num_processes": num_processes,
        },
    )


# Add all subcommands
ingest.add_command(cli_cmds.s3)
ingest.add_command(cli_cmds.google)
ingest.add_command(cli_cmds.dropbox)
ingest.add_command(cli_cmds.azure)


if __name__ == "__main__":
    ingest(obj={})
