import json
import os.path
import typing as t
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.interfaces import (
    EmbeddingConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import ReformatNode
from unstructured.staging.base import convert_to_dict, elements_from_json


@dataclass
class Embedder(ReformatNode):
    embedder_config: EmbeddingConfig
    reprocess: bool = False

    def run(self, elements_json: str) -> str:
        elements_json_filename = os.path.basename(elements_json)
        json_path = (Path(self.get_path()) / elements_json_filename).resolve()
        if not self.reprocess and json_path.is_file() and json_path.stat().st_size:
            logger.debug(f"File exists: {json_path}, skipping embedding")
            return str(json_path)
        elements = elements_from_json(filename=elements_json)
        embedder = self.embedder_config.get_embedder()
        embedded_elements = embedder.embed_documents(elements=elements)
        elements_dict = convert_to_dict(embedded_elements)
        with open(json_path, "w", encoding="utf8") as output_f:
            logger.info(f"writing embeddings content to {json_path}")
            json.dump(elements_dict, output_f, ensure_ascii=False, indent=2)
        return str(json_path)

    def get_path(self) -> t.Optional[Path]:
        return (Path(self.pipeline_config.get_working_dir()) / "embedded").resolve()
