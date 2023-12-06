import typing as t

from unstructured.ingest.interfaces import BaseSourceConnector
from unstructured.ingest.runner.base_runner import Runner

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.local import SimpleLocalConfig


class LocalRunner(Runner):
    connector_config: "SimpleLocalConfig"

    def update_read_config(self):
        pass

    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        from unstructured.ingest.connector.local import (
            LocalSourceConnector,
        )

        return LocalSourceConnector
