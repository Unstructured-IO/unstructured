import hashlib
import logging
from functools import partial
from pathlib import Path

from unstructured.ingest.doc_processor.generalized import process_document
from unstructured.ingest.interfaces import BaseConnector, StandardConnectorConfig
from unstructured.ingest.process import Process


def map_to_standard_config(ctx_dict: dict) -> StandardConnectorConfig:
    return StandardConnectorConfig(
        download_dir=ctx_dict["download_dir"],
        output_dir=ctx_dict["structured_output_dir"],
        download_only=ctx_dict["download_only"],
        fields_include=ctx_dict["fields_include"],
        flatten_metadata=ctx_dict["flatten_metadata"],
        metadata_exclude=ctx_dict["metadata_exclude"],
        metadata_include=ctx_dict["metadata_include"],
        partition_by_api=ctx_dict["partition_by_api"],
        partition_endpoint=ctx_dict["partition_endpoint"],
        preserve_downloads=ctx_dict["preserve_downloads"],
        re_download=ctx_dict["re_download"],
        api_key=ctx_dict["api_key"],
    )


def update_download_dir(ctx_dict: dict, remote_url: str, logger: logging.Logger) -> None:
    if ctx_dict["local_input_path"] is None and not ctx_dict["download_dir"]:
        cache_path = Path.home() / ".cache" / "unstructured" / "ingest"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
        hashed_dir_name = hashlib.sha256(remote_url.encode("utf-8"))
        download_dir = cache_path / hashed_dir_name.hexdigest()[:10]
        if ctx_dict["preserve_downloads"]:
            logger.warning(
                f"Preserving downloaded files but --download-dir is not specified,"
                f" using {download_dir}",
            )
        ctx_dict["download_dir"] = download_dir


def process_documents(doc_connector: BaseConnector, ctx_dict: dict) -> None:
    process_document_with_partition_args = partial(
        process_document,
        strategy=ctx_dict["partition_strategy"],
        ocr_languages=ctx_dict["partition_ocr_languages"],
        encoding=ctx_dict["encoding"],
    )

    Process(
        doc_connector=doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=ctx_dict["num_processes"],
        reprocess=ctx_dict["reprocess"],
        verbose=ctx_dict["verbose"],
        max_docs=ctx_dict["max_docs"],
    ).run()
