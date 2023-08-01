import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleAirtableConfig(BaseConnectorConfig):
    """Connector config where:
    auth_token is the authentication token to authenticate into Airtable.

    Check https://support.airtable.com/docs/airtable-api-key-deprecation-notice
    for more info on authentication.
    """

    personal_access_token: str
    list_of_paths: str


@dataclass
class AirtableFileMeta:
    """Metadata specifying:"""

    base_id: str
    table_id: str
    view_id: Optional[str] = None


# def parse_airtable_path():
#     return

# def parse_list_of_paths(paths_str, sep):
#     paths = paths_str.split(sep)
#     [parse_airtable_path(path) for path in paths]
#     return


@dataclass
class AirtableIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates an Airtable connection object
    to fetch each document, rather than creating a it for each thread.
    """

    config: SimpleAirtableConfig
    file_meta: AirtableFileMeta

    @property
    def filename(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.base_id
            / f"{self.file_meta.table_id}.csv"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, ."""
        output_file = f"{self.file_meta.table_id}.json"
        return Path(self.standard_config.output_dir) / self.file_meta.base_id / output_file

    @requires_dependencies(["pyairtable", "pandas"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process
        import pandas as pd
        from pyairtable import Api

        self.api = Api(self.config.personal_access_token)
        table = self.api.table(self.file_meta.base_id, self.file_meta.table_id)

        df = pd.DataFrame.from_dict([row["fields"] for row in table.all()])
        self.document = df.to_csv()
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@dataclass
class AirtableConnector(ConnectorCleanupMixin, BaseConnector):
    """Fetches tables or views from an Airtable org."""

    config: SimpleAirtableConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleAirtableConfig,
    ):
        super().__init__(standard_config, config)

    @requires_dependencies(["pyairtable"])
    def initialize(self):
        from pyairtable import Api

        if self.config.list_of_paths:
            self.list_of_paths = self.config.list_of_paths.split()

        self.api = Api(self.config.personal_access_token)

    @requires_dependencies(["pyairtable"])
    def _find_and_assign_base_ids(self):
        from pyairtable.metadata import get_api_bases

        self.base_ids = [base["id"] for base in get_api_bases(self.api)["bases"]]

    @requires_dependencies(["pyairtable"])
    def _get_table_ids_within_bases(self):
        from pyairtable.metadata import get_base_schema

        bases = [(base_id, self.api.base(base_id)) for base_id in self.base_ids]

        metadata_for_each_base = [
            (base_id, get_base_schema(base)["tables"]) for base_id, base in bases
        ]

        table_ids_within_bases = [
            (base_id, table["id"])
            for base_id, base_metadata in metadata_for_each_base
            for table in base_metadata
        ]

        return table_ids_within_bases

    def get_ingest_docs(self):
        """Fetches documents in an Airtable org."""
        if not self.config.list_of_paths:
            self._find_and_assign_base_ids()
            table_ids_within_bases = self._get_table_ids_within_bases()

        else:
            # process airtable paths here
            pass

        return [
            AirtableIngestDoc(
                self.standard_config,
                self.config,
                AirtableFileMeta(base_id, table_id),
            )
            for base_id, table_id in table_ids_within_bases
        ]
