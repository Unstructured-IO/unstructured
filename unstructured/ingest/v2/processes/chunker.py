from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from unstructured.chunking import dispatch
from unstructured.documents.elements import Element, assign_and_map_hash_ids
from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.v2.interfaces.process import BaseProcess
from unstructured.ingest.v2.logger import logger
from unstructured.staging.base import dict_to_elements, elements_from_json


@dataclass
class ChunkerConfig(EnhancedDataClassJsonMixin):
    chunking_strategy: Optional[str] = None
    chunking_endpoint: Optional[str] = "https://api.unstructured.io/general/v0/general"
    chunk_by_api: bool = False
    chunk_api_key: Optional[str] = enhanced_field(default=None, sensitive=True)

    chunk_combine_text_under_n_chars: Optional[int] = None
    chunk_include_orig_elements: Optional[bool] = None
    chunk_max_characters: Optional[int] = None
    chunk_multipage_sections: Optional[bool] = None
    chunk_new_after_n_chars: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_overlap_all: Optional[bool] = None

    def to_chunking_kwargs(self) -> dict[str, Any]:
        return {
            "chunking_strategy": self.chunking_strategy,
            "combine_text_under_n_chars": self.chunk_combine_text_under_n_chars,
            "max_characters": self.chunk_max_characters,
            "include_orig_elements": self.chunk_include_orig_elements,
            "multipage_sections": self.chunk_multipage_sections,
            "new_after_n_chars": self.chunk_new_after_n_chars,
            "overlap": self.chunk_overlap,
            "overlap_all": self.chunk_overlap_all,
        }


@dataclass
class Chunker(BaseProcess, ABC):
    config: ChunkerConfig

    def is_async(self) -> bool:
        return self.config.chunk_by_api

    def run(self, elements_filepath: Path, **kwargs: Any) -> list[Element]:
        elements = elements_from_json(filename=str(elements_filepath))
        if not elements:
            return elements
        local_chunking_strategies = ("basic", "by_title")
        if self.config.chunking_strategy not in local_chunking_strategies:
            logger.warning(
                "chunking strategy not supported for local chunking: {}, must be one of: {}".format(
                    self.config.chunking_strategy, ", ".join(local_chunking_strategies)
                )
            )
            return elements
        chunked_elements = dispatch.chunk(elements=elements, **self.config.to_chunking_kwargs())
        assign_and_map_hash_ids(chunked_elements)
        return chunked_elements

    async def run_async(self, elements_filepath: Path, **kwargs: Any) -> list[Element]:
        from unstructured_client import UnstructuredClient
        from unstructured_client.models.shared import Files, PartitionParameters

        client = UnstructuredClient(
            api_key_auth=self.config.chunk_api_key,
            server_url=self.config.chunking_endpoint,
        )
        partition_request = self.config.to_chunking_kwargs()
        with open(elements_filepath, "rb") as f:
            files = Files(
                content=f.read(),
                file_name=str(elements_filepath.resolve()),
            )
            partition_request["files"] = files
        partition_params = PartitionParameters(**partition_request)
        resp = client.general.partition(partition_params)
        elements_raw = resp.elements or []
        elements = dict_to_elements(elements_raw)
        assign_and_map_hash_ids(elements)
        return elements
