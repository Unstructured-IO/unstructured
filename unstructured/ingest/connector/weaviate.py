import json
import os
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

    def __post_init__(self):
        if self.auth_keys:
            self.auth_keys_dict = {
                k: os.getenv(k) for k in self.auth_keys if (os.getenv(k) is not None)
            }

        if self.additional_keys:
            self.additional_keys_dict = {
                k: os.getenv(k) for k in self.additional_keys if (os.getenv(k) is not None)
            }


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

    def conform_dict(self, element: dict) -> None:
        """
        Updates the element dictionary to conform to the Weaviate schema
        """

        if (
            record_locator := element.get("metadata", {})
            .get("data_source", {})
            .get("record_locator")
        ):
            # Explicit casting otherwise fails schema type checking
            element["metadata"]["data_source"]["record_locator"] = str(json.dumps(record_locator))

        if (
            date_modified := element.get("metadata", {})
            .get("data_source", {})
            .get("date_modified", None)
        ):
            element["metadata"]["data_source"]["date_modified"] = date_modified + "Z"

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} rows to destination "
            f"class {self.write_config.class_name} "
            f"at {self.connector_config.host_url}",
        )

        with self.client.batch(batch_size=BATCH_SIZE) as b:
            created = []
            for e in json_list:
                self.conform_dict(e)
                print(e.get("metadata", {}).keys())
                created_id = b.add_data_object(
                    {
                        "type": e.get("type", ""),
                        "element_id": e.get("element_id", ""),
                        "metadata": e.get("metadata", {}),
                        "text": e.get("text", ""),
                    },
                    self.write_config.class_name,
                    vector=e.get("embeddings"),
                )
                created.append(created_id)

            if len(created) < len(json_list):
                raise ValueError(
                    f"Missed {len(json_list)- len(created)} elements.",
                )

            logger.info(f"Wrote {len(created)}/{len(json_list)} elements.")

    @requires_dependencies(["weaviate"], extras="weaviate")
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
