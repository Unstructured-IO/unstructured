import typing as t
from dataclasses import dataclass

from unstructured.ingest.pipeline.interfaces import DocFactoryNode


@dataclass
class DocFactory(DocFactoryNode):
    def run(self, *args, **kwargs) -> t.Iterable[str]:
        docs = self.source_doc_connector.get_ingest_docs()
        json_docs = [doc.to_json() for doc in docs]
        return json_docs
