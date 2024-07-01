from __future__ import annotations

import hashlib
import json
import os.path
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from unstructured.chunking import dispatch
from unstructured.documents.elements import Element, assign_and_map_hash_ids
from unstructured.ingest.interfaces import ChunkingConfig, PartitionConfig
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import ReformatNode
from unstructured.partition.api import partition_via_api
from unstructured.staging.base import elements_from_json, elements_to_dicts


@dataclass
class Chunker(ReformatNode):
    """Implementation for the chunking node in the ingest pipeline.

    Parameters
    ----------
    pipeline_context: PipelineContext (inherited from parent class)
    chunking_config: ChunkingConfig
    partition_config: PartitionConfig
    """

    chunking_config: ChunkingConfig
    partition_config: PartitionConfig

    def initialize(self):
        logger.info(
            f"Running chunking node. Chunking config: {self.chunking_config.to_json()}]",
        )
        super().initialize()

    def create_hash(self) -> str:
        hash_dict = self.chunking_config.to_dict()
        return hashlib.sha256(json.dumps(hash_dict, sort_keys=True).encode()).hexdigest()[:32]

    def run(self, elements_json: str) -> Optional[str]:
        try:
            elements_json_filename = os.path.basename(elements_json)
            filename_ext = os.path.basename(elements_json_filename)
            filename = os.path.splitext(filename_ext)[0]
            hashed_filename = hashlib.sha256(
                f"{self.create_hash()}{filename}".encode(),
            ).hexdigest()[:32]
            json_filename = f"{hashed_filename}.json"
            json_path = (Path(self.get_path()) / json_filename).resolve()
            self.pipeline_context.ingest_docs_map[hashed_filename] = (
                self.pipeline_context.ingest_docs_map[filename]
            )
            if (
                not self.pipeline_context.reprocess
                and json_path.is_file()
                and json_path.stat().st_size
            ):
                logger.debug(f"File exists: {json_path}, skipping chunking")
                return str(json_path)

            chunked_elements = self.chunk(elements_json)

            # -- return if chunking_strategy is None --
            if chunked_elements is None:
                logger.info(f"chunking_strategy is None, skipping chunking for {filename_ext}")
                return

            assign_and_map_hash_ids(chunked_elements)

            element_dicts = elements_to_dicts(chunked_elements)
            with open(json_path, "w", encoding="utf8") as output_f:
                logger.info(f"writing chunking content to {json_path}")
                json.dump(element_dicts, output_f, ensure_ascii=False, indent=2)
                return str(json_path)

        except Exception as e:
            if self.pipeline_context.raise_on_error:
                raise
            logger.error(f"failed to run chunking on file {elements_json}, {e}", exc_info=True)
            return None

    def get_path(self) -> Path:
        return (Path(self.pipeline_context.work_dir) / "chunked").resolve()

    def chunk(self, elements_json_file: str) -> Optional[list[Element]]:
        """Called by Chunker.run() to properly execute the defined chunking_strategy."""
        # -- No chunking_strategy means no chunking --
        if self.chunking_config.chunking_strategy is None:
            return
        # -- Chunk locally for open-source chunking strategies, even when partitioning remotely --
        if self.chunking_config.chunking_strategy in ("basic", "by_title"):
            return dispatch.chunk(
                elements=elements_from_json(filename=elements_json_file),
                chunking_strategy=self.chunking_config.chunking_strategy,
                combine_text_under_n_chars=self.chunking_config.combine_text_under_n_chars,
                include_orig_elements=self.chunking_config.include_orig_elements,
                max_characters=self.chunking_config.max_characters,
                multipage_sections=self.chunking_config.multipage_sections,
                new_after_n_chars=self.chunking_config.new_after_n_chars,
                overlap=self.chunking_config.overlap,
                overlap_all=self.chunking_config.overlap_all,
            )
        # -- Chunk remotely --
        if self.partition_config.partition_by_api:
            return partition_via_api(
                filename=elements_json_file,
                # -- (jennings) If api_key or api_url are None, partition_via_api will raise an
                # -- error, which will be caught and logged by Chunker.run()
                api_key=self.partition_config.api_key,  # type: ignore
                api_url=self.partition_config.partition_endpoint,  # type: ignore
                chunking_strategy=self.chunking_config.chunking_strategy,
                combine_under_n_chars=self.chunking_config.combine_text_under_n_chars,
                include_orig_elements=self.chunking_config.include_orig_elements,
                max_characters=self.chunking_config.max_characters,
                multipage_sections=self.chunking_config.multipage_sections,
                new_after_n_chars=self.chunking_config.new_after_n_chars,
                overlap=self.chunking_config.overlap,
                overlap_all=self.chunking_config.overlap_all,
            )
        # -- Warn that the defined chunking_strategy is not locally available --
        logger.warning(
            f"There is no locally available chunking_strategy:"
            f" {self.chunking_config.chunking_strategy}."
            f" If trying to partition remotely, check that `partition_by_api`, `api_url`,"
            f" and `api_key` are correctly defined."
        )
