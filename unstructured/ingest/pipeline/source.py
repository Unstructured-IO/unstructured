import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.interfaces import BaseSessionHandle, IngestDocSessionHandleMixin
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import SourceNode

# module-level variable to store session handle
session_handle: t.Optional[BaseSessionHandle] = None


@dataclass
class Reader(SourceNode):
    def run(self, ingest_doc_dict: dict) -> t.Optional[str]:
        try:
            global session_handle
            doc = create_ingest_doc_from_dict(ingest_doc_dict)
            filename = doc.filename
            if not self.read_config.re_download and filename.is_file() and filename.stat().st_size:
                logger.info(f"File exists: {filename}, skipping download")
                return filename
            if isinstance(doc, IngestDocSessionHandleMixin):
                if session_handle is None:
                    # create via doc.session_handle, which is a property that creates a
                    # session handle if one is not already defined
                    session_handle = doc.session_handle
                else:
                    doc.session_handle = session_handle
            # does the work necessary to load file into filesystem
            # in the future, get_file_handle() could also be supported
            if self.retry_strategy:
                self.retry_strategy(doc.get_file)
            else:
                doc.get_file()
            for k, v in doc.to_dict().items():
                ingest_doc_dict[k] = v
            return doc.filename
        except Exception as e:
            if self.pipeline_context.raise_on_error:
                raise
            logger.error(
                f"failed to get data associated with source doc: {ingest_doc_dict}, {e}",
                exc_info=True,
            )
            return None
