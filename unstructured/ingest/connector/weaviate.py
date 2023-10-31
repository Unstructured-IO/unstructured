import json
import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

BATCH_SIZE = 100


@dataclass
class SimpleWeaviateConfig(BaseConnectorConfig):
    host_url: str
    auth_keys: t.Optional[t.List[str]] = None
    additional_keys: t.Optional[t.List[str]] = None


@dataclass
class WeaviateWriteConfig(WriteConfig):
    class_name: str


@dataclass
class WeaviateDestinationConnector(BaseDestinationConnector):
    write_config: WeaviateWriteConfig
    connector_config: SimpleWeaviateConfig

    @requires_dependencies(["weaviate"], extras="weaviate")
    def initialize(self):
        from weaviate import Client

        self.client: Client = Client(
            url=self.connector_config.host_url,
        )

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} rows to destination "
            f"class {self.write_config.class_name} "
            f"at {self.write_config.host_url}",
        )

        with self.client.batch(batch_size=BATCH_SIZE) as b:
            created = []
            for e in json_list:
                created_id = b.add_data_object(
                    {
                        "type": e.get("type", ""),
                        "element_id": e.get("element_id", ""),
                        "metadata": e.get("metadata", {}),
                        "text": e.get("text", ""),
                    },
                    self.write_config.class_name,
                )
                created.append(created_id)

            if len(created) < len(json_list):
                raise ValueError(
                    f"Missed {len(json_list)- len(created)} elements.",
                )

            logger.info(f"Wrote {len(created)}/{len(json_list)} elements.")

    @requires_dependencies(["deltalake"], extras="delta-table")
    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                json_content = json.load(json_file)
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        self.write_dict(json_list=json_list)
