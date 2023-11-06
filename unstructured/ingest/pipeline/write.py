import os.path
import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.pipeline.interfaces import WriteNode


@dataclass
class Writer(WriteNode):
    def run(self, json_paths: t.List[str]):
        ingest_docs = []
        for json_path in json_paths:
            filename = os.path.basename(json_path)
            doc_hash = os.path.splitext(filename)[0]
            ingest_doc_dict = self.pipeline_context.ingest_docs_map[doc_hash]
            ingest_docs.append(create_ingest_doc_from_dict(ingest_doc_dict))
        self.dest_doc_connector.write(docs=ingest_docs)
