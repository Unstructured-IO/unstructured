import os
import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.interfaces import (
    BaseIngestDocBatch,
    BaseSessionHandle,
    BaseSingleIngestDoc,
    IngestDocSessionHandleMixin,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import SourceNode

# module-level variable to store session handle
session_handle: t.Optional[BaseSessionHandle] = None


@dataclass
class Reader(SourceNode):
    def get_single(self, doc: BaseSingleIngestDoc, ingest_doc_dict: dict) -> str:
        if (
            not self.read_config.re_download
            and doc.filename.is_file()
            and doc.filename.stat().st_size
        ):
            logger.info(f"File exists: {doc.filename}, skipping download")
            # Still need to fetch metadata if file exists locally
            doc.update_source_metadata()
        else:
            # TODO: update all to use doc.to_json(redact_sensitive=True) once session handler
            # can be serialized
            try:
                serialized_doc = doc.to_json(redact_sensitive=True)
                logger.debug(f"Fetching {serialized_doc} - PID: {os.getpid()}")
            except Exception as e:
                logger.warning("failed to print full doc: ", e)
                logger.debug(f"Fetching {doc.__class__.__name__} - PID: {os.getpid()}")
            if self.retry_strategy:
                self.retry_strategy(doc.get_file)
            else:
                doc.get_file()
        for k, v in doc.to_dict().items():
            ingest_doc_dict[k] = v
        return doc.filename

    def get_batch(self, doc_batch: BaseIngestDocBatch, ingest_doc_dict: dict) -> t.List[str]:
        if self.retry_strategy:
            self.retry_strategy(doc_batch.get_files)
        else:
            doc_batch.get_files()
        for k, v in doc_batch.to_dict().items():
            ingest_doc_dict[k] = v
        return [doc.filename for doc in doc_batch.ingest_docs]

    def run(self, ingest_doc_dict: dict) -> t.Optional[t.Union[str, t.List[str]]]:
        try:
            global session_handle
            doc = create_ingest_doc_from_dict(ingest_doc_dict)
            if isinstance(doc, IngestDocSessionHandleMixin):
                if session_handle is None:
                    # create via doc.session_handle, which is a property that creates a
                    # session handle if one is not already defined
                    session_handle = doc.session_handle
                else:
                    doc._session_handle = session_handle
            if isinstance(doc, BaseSingleIngestDoc):
                return self.get_single(doc=doc, ingest_doc_dict=ingest_doc_dict)
            elif isinstance(doc, BaseIngestDocBatch):
                return self.get_batch(doc_batch=doc, ingest_doc_dict=ingest_doc_dict)
            else:
                raise ValueError(
                    f"type of doc ({type(doc)}) is not a recognized type: "
                    f"BaseSingleIngestDoc or BaseSingleIngestDoc"
                )
        except Exception as e:
            if self.pipeline_context.raise_on_error:
                raise
            logger.error(
                f"failed to get data associated with source doc: {ingest_doc_dict}, {e}",
                exc_info=True,
            )
            return None
