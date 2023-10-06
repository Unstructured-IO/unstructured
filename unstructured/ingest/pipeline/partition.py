import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.connector.registry import create_ingest_doc_from_json
from unstructured.ingest.error import PartitionError
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import PartitionNode
from unstructured.ingest.pipeline.utils import get_ingest_doc_hash


@dataclass
class Partitioner(PartitionNode):
    @PartitionError.wrap
    def run(self, ingest_doc_json) -> str:
        doc = create_ingest_doc_from_json(ingest_doc_json)
        doc_filename_hash = get_ingest_doc_hash(ingest_doc_json)
        hashed_filename = hashlib.sha256(
            f"{self.create_hash()}{doc_filename_hash}".encode(),
        ).hexdigest()[:32]
        self.pipeline_context.ingest_docs_map[hashed_filename] = ingest_doc_json
        doc_filename = f"{hashed_filename}.json"
        json_path = (Path(self.get_path()) / doc_filename).resolve()
        if not self.pipeline_context.reprocess and json_path.is_file() and json_path.stat().st_size:
            logger.info(f"File exists: {json_path}, skipping partition")
            return str(json_path)
        languages = (
            self.partition_config.ocr_languages.split("+")
            if self.partition_config.ocr_languages
            else []
        )
        elements = doc.process_file(
            partition_config=self.partition_config,
            strategy=self.partition_config.strategy,
            languages=languages,
            encoding=self.partition_config.encoding,
            pdf_infer_table_structure=self.partition_config.pdf_infer_table_structure,
        )
        with open(json_path, "w", encoding="utf8") as output_f:
            logger.info(f"writing partitioned content to {json_path}")
            json.dump(elements, output_f, ensure_ascii=False, indent=2)
        return str(json_path)
