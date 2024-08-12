import json
import typing as t
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.utils.data_prep import batch_generator
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    UploadContent,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)
from unstructured.ingest.v2.processes.connectors.utils import parse_datetime
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from azure.search.documents import SearchClient


CONNECTOR_TYPE = "azure_cognitive_search"


@dataclass
class AzureCognitiveSearchAccessConfig(AccessConfig):
    key: t.Optional[str] = enhanced_field(default=None, overload_name="azure_cognitive_search_key")


@dataclass
class AzureCognitiveSearchConnectionConfig(ConnectionConfig):
    endpoint: str
    index: str
    access_config: AzureCognitiveSearchAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["azure.search", "azure.core"], extras="azure-cognitive-search")
    def generate_client(self) -> "SearchClient":
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index,
            credential=AzureKeyCredential(self.access_config.key),
        )


@dataclass
class AzureCognitiveSearchUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class AzureCognitiveSearchUploaderConfig(UploaderConfig):
    batch_size: int = 100


@dataclass
class AzureCognitiveSearchUploadStager(UploadStager):
    upload_stager_config: AzureCognitiveSearchUploadStagerConfig = field(
        default_factory=lambda: AzureCognitiveSearchUploadStagerConfig()
    )

    @staticmethod
    def conform_dict(data: dict) -> dict:
        """
        updates the dictionary that is from each Element being converted into a dict/json
        into a dictionary that conforms to the schema expected by the
        Azure Cognitive Search index
        """

        data["id"] = str(uuid.uuid4())

        if points := data.get("metadata", {}).get("coordinates", {}).get("points"):
            data["metadata"]["coordinates"]["points"] = json.dumps(points)
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            data["metadata"]["data_source"]["record_locator"] = json.dumps(record_locator)
        if permissions_data := (
            data.get("metadata", {}).get("data_source", {}).get("permissions_data")
        ):
            data["metadata"]["data_source"]["permissions_data"] = json.dumps(permissions_data)
        if links := data.get("metadata", {}).get("links"):
            data["metadata"]["links"] = [json.dumps(link) for link in links]
        if last_modified := data.get("metadata", {}).get("last_modified"):
            data["metadata"]["last_modified"] = parse_datetime(last_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = parse_datetime(date_created).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = parse_datetime(
                date_modified
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = parse_datetime(
                date_processed
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = json.dumps(regex_metadata)
        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)
        return data

    def run(
        self,
        elements_filepath: Path,
        output_dir: Path,
        output_filename: str,
        **kwargs: t.Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents = json.load(elements_file)

        conformed_elements = [self.conform_dict(data=element) for element in elements_contents]

        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        with open(output_path, "w") as output_file:
            json.dump(conformed_elements, output_file)
        return output_path


@dataclass
class AzureCognitiveSearchUploader(Uploader):
    upload_config: AzureCognitiveSearchUploaderConfig
    connection_config: AzureCognitiveSearchConnectionConfig
    connector_type: str = CONNECTOR_TYPE

    @DestinationConnectionError.wrap
    @requires_dependencies(["azure"], extras="azure-cognitive-search")
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        import azure.core.exceptions

        logger.info(
            f"writing {len(elements_dict)} documents to destination "
            f"index at {self.connection_config.index}",
        )
        try:
            results = self.connection_config.generate_client().upload_documents(
                documents=elements_dict
            )

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

    def write_dict_wrapper(self, elements_dict):
        return self.write_dict(elements_dict=elements_dict)

    def run(self, contents: list[UploadContent], **kwargs: t.Any) -> None:

        elements_dict = []
        for content in contents:
            with open(content.path) as elements_file:
                elements = json.load(elements_file)
                elements_dict.extend(elements)

        logger.info(
            f"writing document batches to destination"
            f" endpoint at {str(self.connection_config.endpoint)}"
            f" index at {str(self.connection_config.index)}"
            f" with batch size {str(self.upload_config.batch_size)}"
        )

        batch_size = self.upload_config.batch_size

        for chunk in batch_generator(elements_dict, batch_size):
            self.write_dict(elements_dict=chunk)  # noqa: E203


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=AzureCognitiveSearchConnectionConfig,
        uploader=AzureCognitiveSearchUploader,
        uploader_config=AzureCognitiveSearchUploaderConfig,
        upload_stager=AzureCognitiveSearchUploadStager,
        upload_stager_config=AzureCognitiveSearchUploadStagerConfig,
    ),
)
