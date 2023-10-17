import json
import typing as t
import uuid
from dataclasses import dataclass

import azure.core.exceptions

from unstructured.ingest.error import WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleAzureCognitiveSearchStorageConfig(BaseConnectorConfig):
    endpoint: str
    key: str


@dataclass
class AzureCognitiveSearchWriteConfig(WriteConfig):
    index: str


@dataclass
class AzureCognitiveSearchDestinationConnector(BaseDestinationConnector):
    write_config: AzureCognitiveSearchWriteConfig
    connector_config: SimpleAzureCognitiveSearchStorageConfig

    @requires_dependencies(["azure"], extras="azure-cognitive-search")
    def initialize(self):
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        # Create a client
        credential = AzureKeyCredential(self.connector_config.key)
        self.client = SearchClient(
            endpoint=self.connector_config.endpoint,
            index_name=self.write_config.index,
            credential=credential,
        )

    def conform_dict(self, data: dict) -> None:
        """
        updates the dictionary that is from each Element being converted into a dict/json
        into a dictionary that conforms to the schema expected by the
        Azure Cognitive Search index
        """
        from dateutil import parser  # type: ignore

        data["id"] = str(uuid.uuid4())

        if points := data.get("metadata", {}).get("coordinates", {}).get("points"):
            data["metadata"]["coordinates"]["points"] = json.dumps(points)
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            data["metadata"]["data_source"]["record_locator"] = json.dumps(record_locator)
        if last_modified := data.get("metadata", {}).get("last_modified"):
            data["metadata"]["last_modified"] = parser.parse(last_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = parser.parse(date_created).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )
        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = parser.parse(date_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )
        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = parser.parse(
                date_processed,
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = json.dumps(regex_metadata)
        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} documents to destination "
            f"index at {self.write_config.index}",
        )
        try:
            results = self.client.upload_documents(documents=json_list)

        except azure.core.exceptions.HttpResponseError as http_error:
            raise WriteError(f"http error: {http_error}") from http_error
        errors = []
        success = []
        for result in results:
            if result.succeeded:
                success.append(result)
            else:
                errors.append(result)
        logger.debug(f"results: {len(success)} successes, {len(errors)} failures")
        if errors:
            raise WriteError(
                ", ".join(
                    [
                        f"{error.key}: [{error.status_code}] {error.error_message}"
                        for error in errors
                    ],
                ),
            )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                json_content = json.load(json_file)
                for content in json_content:
                    self.conform_dict(data=content)
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        self.write_dict(json_list=json_list)
