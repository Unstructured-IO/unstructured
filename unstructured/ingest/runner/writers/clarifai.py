import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.clarifai import ClarifaiWriteConfig, SimpleClarifaiConfig


@dataclass
class ClarifaiWriter(Writer):
    write_config: "ClarifaiWriteConfig"
    connector_config: "SimpleClarifaiConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.clarifai import ClarifaiDestinationConnector

        return ClarifaiDestinationConnector
