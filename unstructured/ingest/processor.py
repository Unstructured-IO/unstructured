import logging
import multiprocessing as mp
import typing as t
from contextlib import suppress
from functools import partial

from unstructured.ingest.doc_processor.generalized import initialize, process_document
from unstructured.ingest.interfaces import (
    BaseDestinationConnector,
    BaseSourceConnector,
    PartitionConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger

with suppress(RuntimeError):
    mp.set_start_method("spawn")


class Processor:
    def __init__(
        self,
        source_doc_connector: BaseSourceConnector,
        doc_processor_fn,
        num_processes: int,
        reprocess: bool,
        verbose: bool,
        max_docs: t.Optional[int],
        dest_doc_connector: t.Optional[BaseDestinationConnector] = None,
    ):
        # initialize the reader and writer
        self.source_doc_connector = source_doc_connector
        self.doc_processor_fn = doc_processor_fn
        self.num_processes = num_processes
        self.reprocess = reprocess
        self.verbose = verbose
        self.max_docs = max_docs
        self.dest_doc_connector = dest_doc_connector

    def initialize(self):
        """Slower initialization things: check connections, load things into memory, etc."""
        ingest_log_streaming_init(logging.DEBUG if self.verbose else logging.INFO)
        self.source_doc_connector.initialize()
        if self.dest_doc_connector:
            self.dest_doc_connector.initialize()
        initialize()

    def cleanup(self):
        self.source_doc_connector.cleanup()

    def _filter_docs_with_outputs(self, docs):
        num_docs_all = len(docs)
        docs = [doc for doc in docs if not doc.has_output()]
        if self.max_docs is not None:
            if num_docs_all > self.max_docs:
                num_docs_all = self.max_docs
            docs = docs[: self.max_docs]
        num_docs_to_process = len(docs)
        if num_docs_to_process == 0:
            logger.info(
                "All docs have structured outputs, nothing to do. Use --reprocess to process all.",
            )
            return None
        elif num_docs_to_process != num_docs_all:
            logger.info(
                f"Skipping processing for {num_docs_all - num_docs_to_process} docs out of "
                f"{num_docs_all} since their structured outputs already exist, use --reprocess to "
                "reprocess those in addition to the unprocessed ones.",
            )
        return docs

    def run_partition(self, docs):
        if not self.reprocess:
            docs = self._filter_docs_with_outputs(docs)
            if not docs:
                return

        # Debugging tip: use the below line and comment out the mp.Pool loop
        # block to remain in single process
        # self.doc_processor_fn(docs[0])
        logger.info(f"Processing {len(docs)} docs")
        json_docs = [doc.to_json() for doc in docs]
        with mp.Pool(
            processes=self.num_processes,
            initializer=ingest_log_streaming_init,
            initargs=(logging.DEBUG if self.verbose else logging.INFO,),
        ) as pool:
            pool.map(self.doc_processor_fn, json_docs)

    def run(self):
        self.initialize()

        # fetch the list of lazy downloading IngestDoc obj's
        docs = self.source_doc_connector.get_ingest_docs()

        try:
            self.run_partition(docs=docs)
            if self.dest_doc_connector:
                self.dest_doc_connector.write(docs=docs)
        finally:
            self.cleanup()


def process_documents(
    source_doc_connector: BaseSourceConnector,
    partition_config: PartitionConfig,
    verbose: bool,
    dest_doc_connector: t.Optional[BaseDestinationConnector] = None,
) -> None:
    process_document_with_partition_args = partial(
        process_document,
        strategy=partition_config.strategy,
        ocr_languages=partition_config.ocr_languages,
        encoding=partition_config.encoding,
        pdf_infer_table_structure=partition_config.pdf_infer_table_structure,
    )

    Processor(
        source_doc_connector=source_doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=partition_config.num_processes,
        reprocess=partition_config.reprocess,
        verbose=verbose,
        max_docs=partition_config.max_docs,
        dest_doc_connector=dest_doc_connector,
    ).run()
