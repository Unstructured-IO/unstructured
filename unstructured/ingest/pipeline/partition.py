import hashlib
import json
import typing as t
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.error import PartitionError
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import PartitionNode
from unstructured.ingest.pipeline.utils import get_ingest_doc_hash


@dataclass
class Partitioner(PartitionNode):
    @PartitionError.wrap
    def run(self, ingest_doc_dict) -> Optional[str]:
        try:
            doc = create_ingest_doc_from_dict(ingest_doc_dict)
            doc_filename_hash = get_ingest_doc_hash(ingest_doc_dict)
            hashed_filename = hashlib.sha256(
                f"{self.create_hash()}{doc_filename_hash}".encode(),
            ).hexdigest()[:32]
            self.pipeline_context.ingest_docs_map[hashed_filename] = ingest_doc_dict
            doc_filename = f"{hashed_filename}.json"
            json_path = (Path(self.get_path()) / doc_filename).resolve()
            if (
                not self.pipeline_context.reprocess
                and json_path.is_file()
                and json_path.stat().st_size
            ):
                logger.info(f"File exists: {json_path}, skipping partition")
                return str(json_path)
            partition_kwargs: t.Dict[str, t.Any] = {
                "strategy": self.partition_config.strategy,
                "encoding": self.partition_config.encoding,
                "pdf_infer_table_structure": self.partition_config.pdf_infer_table_structure,
                "languages": self.partition_config.ocr_languages,
                "hi_res_model_name": self.partition_config.hi_res_model_name,
            }
            if self.partition_config.skip_infer_table_types:
                partition_kwargs["skip_infer_table_types"] = (
                    self.partition_config.skip_infer_table_types
                )
            if self.partition_config.additional_partition_args:
                partition_kwargs.update(self.partition_config.additional_partition_args)
            elements = doc.process_file(
                partition_config=self.partition_config,
                **partition_kwargs,
            )
            with open(json_path, "w", encoding="utf8") as output_f:
                logger.info(f"writing partitioned content to {json_path}")
                json.dump(elements, output_f, ensure_ascii=False, indent=2, sort_keys=True)
            return str(json_path)
        except Exception as e:
            if self.pipeline_context.raise_on_error:
                raise
            logger.error(f"failed to partition doc: {ingest_doc_dict}, {e}", exc_info=True)
            return None
