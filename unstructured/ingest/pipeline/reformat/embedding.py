import hashlib
import json
import os.path
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

    def initialize(self):
        logger.info(
            f"Running embedding node. Embedding config: {self.embedder_config.to_json()}]",
        )
        super().initialize()

    def create_hash(self) -> str:
        hash_dict = self.embedder_config.to_dict()
        return hashlib.sha256(json.dumps(hash_dict, sort_keys=True).encode()).hexdigest()[:32]

    def run(self, elements_json: str) -> str:
        elements_json_filename = os.path.basename(elements_json)
        filename_ext = os.path.basename(elements_json_filename)
        filename = os.path.splitext(filename_ext)[0]
        hashed_filename = hashlib.sha256(f"{self.create_hash()}{filename}".encode()).hexdigest()[
            :32
        ]
        json_filename = f"{hashed_filename}.json"
        json_path = (Path(self.get_path()) / json_filename).resolve()
        if not self.pipeline_context.reprocess and json_path.is_file() and json_path.stat().st_size:
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

    def get_path(self) -> Path:
        return (Path(self.pipeline_context.work_dir) / "embedded").resolve()
