import os.path
import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.interfaces import BaseSingleIngestDoc
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import WriteNode


@dataclass
class Writer(WriteNode):
    def run(self, json_paths: t.List[str]):
        ingest_docs: t.List[BaseSingleIngestDoc] = []
        for json_path in json_paths:
            filename = os.path.basename(json_path)
            doc_hash = os.path.splitext(filename)[0]
            ingest_doc_dict = self.pipeline_context.ingest_docs_map[doc_hash]
            single_ingest_doc = create_ingest_doc_from_dict(ingest_doc_dict)
            if isinstance(single_ingest_doc, BaseSingleIngestDoc):
                ingest_docs.append(single_ingest_doc)
            else:
                logger.warning(
                    f"deserialized ingest doc to write but not of "
                    f"expected instance type (BaseSingleIngestDoc): "
                    f"{type(single_ingest_doc)}"
                )
        self.dest_doc_connector.write(docs=ingest_docs)
