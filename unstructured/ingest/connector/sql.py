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

ENGINE_DB_MAPPING ={
    'postgres': 'psycopg2'
}


@dataclass
class SimpleSqlConfig(BaseConnectorConfig):
    db_name: str
    username: str
    password: str
    host: str
    database: str
    port: int = 5432

    @property
    def db_url(self):
        from sqlalchemy.engine.url import URL
        return URL.create(
            drivername=ENGINE_DB_MAPPING.get('postgres'),
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )


@dataclass
class SqlWriteConfig(WriteConfig):
    mode: t.Literal["error", "append", "overwrite"] = "error"


@dataclass
class SqlDestinationConnector(BaseDestinationConnector):
    write_config: SqlWriteConfig
    connector_config: SimpleSqlConfig

    @requires_dependencies(["sqlalchemy"], extras="sql")
    def initialize(self):
        from sqlalchemy import create_engine
        self.engine = create_engine(self.connector_config.db_url)

    def conform_dict(self, element: dict) -> None:
        """
        Updates the element dictionary to conform to the sql schema
        """

        pass

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} objects to destination "
            f"class {self.write_config.class_name} "
            f"at {self.connector_config.host_url}",
        )
        pass

    @requires_dependencies(["sqlalchemy"], extras="sql")
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
