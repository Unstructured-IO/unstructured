from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.enhanced_dataclass.dataclasses import enhanced_field
from unstructured.ingest.v2.interfaces.process import BaseProcess
from unstructured.ingest.v2.logger import logger
from unstructured.staging.base import elements_to_dicts, flatten_dict


@dataclass
class PartitionerConfig(EnhancedDataClassJsonMixin):
    strategy: str = "auto"
    ocr_languages: Optional[list[str]] = None
    encoding: Optional[str] = None
    additional_partition_args: dict[str, Any] = field(default_factory=dict)
    skip_infer_table_types: Optional[list[str]] = None
    fields_include: list[str] = field(
        default_factory=lambda: ["element_id", "text", "type", "metadata", "embeddings"],
    )
    flatten_metadata: bool = False
    metadata_exclude: list[str] = field(default_factory=list)
    metadata_include: list[str] = field(default_factory=list)
    partition_endpoint: Optional[str] = "https://api.unstructured.io/general/v0/general"
    partition_by_api: bool = False
    api_key: Optional[str] = enhanced_field(default=None, sensitive=True)
    hi_res_model_name: Optional[str] = None

    def __post_init__(self):
        if self.metadata_exclude and self.metadata_include:
            raise ValueError(
                "metadata_exclude and metadata_include are "
                "mutually exclusive with each other. Cannot specify both."
            )

    def to_partition_kwargs(self) -> dict[str, Any]:
        partition_kwargs: dict[str, Any] = {
            "strategy": self.strategy,
            "languages": self.ocr_languages,
            "hi_res_model_name": self.hi_res_model_name,
            "skip_infer_table_types": self.skip_infer_table_types,
        }
        # Don't inject information if None and allow default values in method to be used
        partition_kwargs = {k: v for k, v in partition_kwargs.items() if v is not None}
        if self.additional_partition_args:
            partition_kwargs.update(self.additional_partition_args)
        return partition_kwargs


@dataclass
class Partitioner(BaseProcess, ABC):
    config: PartitionerConfig

    def is_async(self) -> bool:
        return self.config.partition_by_api

    def postprocess(self, elements: list[dict]) -> list[dict]:
        element_dicts = [e.copy() for e in elements]
        for elem in element_dicts:
            if self.config.metadata_exclude:
                ex_list = self.config.metadata_exclude
                for ex in ex_list:
                    if "." in ex:  # handle nested fields
                        nested_fields = ex.split(".")
                        current_elem = elem
                        for f in nested_fields[:-1]:
                            if f in current_elem:
                                current_elem = current_elem[f]
                        field_to_exclude = nested_fields[-1]
                        if field_to_exclude in current_elem:
                            current_elem.pop(field_to_exclude, None)
                    else:  # handle top-level fields
                        elem["metadata"].pop(ex, None)  # type: ignore[attr-defined]
            elif self.config.metadata_include:
                in_list = self.config.metadata_include
                for k in list(elem["metadata"].keys()):  # type: ignore[attr-defined]
                    if k not in in_list:
                        elem["metadata"].pop(k, None)  # type: ignore[attr-defined]
            in_list = self.config.fields_include
            elem = {k: v for k, v in elem.items() if k in in_list}

            if self.config.flatten_metadata and "metadata" in elem:
                metadata = elem.pop("metadata")
                elem.update(flatten_dict(metadata, keys_to_omit=["data_source_record_locator"]))
        return element_dicts

    def run(
        self, filename: Path, metadata: Optional[DataSourceMetadata] = None, **kwargs
    ) -> list[dict]:
        from unstructured.partition.auto import partition

        logger.debug(f"Using local partition with kwargs: {self.config.to_partition_kwargs()}")
        logger.info(f"partitioning file {filename} with metadata {metadata.to_dict()}")
        elements = partition(
            filename=str(filename.resolve()),
            data_source_metadata=metadata,
            **self.config.to_partition_kwargs(),
        )
        return self.postprocess(elements=elements_to_dicts(elements))

    async def run_async(
        self, filename: Path, metadata: Optional[DataSourceMetadata] = None, **kwargs
    ) -> list[dict]:
        from unstructured_client import UnstructuredClient
        from unstructured_client.models.shared import Files, PartitionParameters

        logger.info(f"partitioning file {filename} with metadata: {metadata.to_dict()}")
        client = UnstructuredClient(
            server_url=self.config.partition_endpoint, api_key_auth=self.config.api_key
        )
        partition_request = self.config.to_partition_kwargs()
        logger.debug(f"Using hosted partitioner with kwargs: {partition_request}")
        with open(filename, "rb") as f:
            files = Files(
                content=f.read(),
                file_name=str(filename.resolve()),
            )
            partition_request["files"] = files
        partition_params = PartitionParameters(**partition_request)
        resp = client.general.partition(partition_params)
        elements = resp.elements or []
        # Append the data source metadata the auto partition does for you
        for element in elements:
            element["metadata"]["data_source"] = metadata.to_dict()
        return self.postprocess(elements=elements)
