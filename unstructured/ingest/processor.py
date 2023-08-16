import logging
import multiprocessing as mp
from contextlib import suppress
from functools import partial

from unstructured.ingest.doc_processor.generalized import initialize, process_document
from unstructured.ingest.interfaces import (
    BaseConnector,
    ProcessorConfigs,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger

with suppress(RuntimeError):
    mp.set_start_method("spawn")


class Processor:
    def __init__(
        self,
        doc_connector,
        doc_processor_fn,
        num_processes,
        reprocess,
        verbose,
        max_docs,
    ):
        # initialize the reader and writer
        self.doc_connector = doc_connector
        self.doc_processor_fn = doc_processor_fn
        self.num_processes = num_processes
        self.reprocess = reprocess
        self.verbose = verbose
        self.max_docs = max_docs

    def initialize(self):
        """Slower initialization things: check connections, load things into memory, etc."""
        ingest_log_streaming_init(logging.DEBUG if self.verbose else logging.INFO)
        self.doc_connector.initialize()
        initialize()

    def cleanup(self):
        self.doc_connector.cleanup()

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

    def run(self):
        self.initialize()

        # fetch the list of lazy downloading IngestDoc obj's
        docs = self.doc_connector.get_ingest_docs()

        # remove docs that have already been processed
        if not self.reprocess:
            docs = self._filter_docs_with_outputs(docs)
            if not docs:
                return

        # Debugging tip: use the below line and comment out the mp.Pool loop
        # block to remain in single process
        # self.doc_processor_fn(docs[0])
        logger.info(f"Processing {len(docs)} docs")
        try:
            with mp.Pool(
                processes=self.num_processes,
                initializer=ingest_log_streaming_init,
                initargs=(logging.DEBUG if self.verbose else logging.INFO,),
            ) as pool:
                pool.map(self.doc_processor_fn, docs)
        finally:
            self.cleanup()


def process_documents(
    doc_connector: BaseConnector,
    processor_config: ProcessorConfigs,
    verbose=bool,
) -> None:
    process_document_with_partition_args = partial(
        process_document,
        strategy=processor_config.partition_strategy,
        ocr_languages=processor_config.partition_ocr_languages,
        encoding=processor_config.partition_encoding,
        pdf_infer_table_structure=processor_config.partition_pdf_infer_table_structure,
    )

    Processor(
        doc_connector=doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=processor_config.num_processes,
        reprocess=processor_config.reprocess,
        verbose=verbose,
        max_docs=processor_config.max_docs,
    ).run()
