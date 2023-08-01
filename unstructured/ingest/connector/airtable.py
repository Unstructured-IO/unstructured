import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pyairtable import Api
from pyairtable.metadata import get_api_bases, get_base_schema

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
            / f"{self.file_meta.table_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, ."""
        output_file = f"{self.file_meta.table_id}.txt"
        return Path(self.standard_config.output_dir) / self.file_meta.base_id / output_file

    def _flatten_values(self, value, seperator="\n", no_value_str=""):
        """Flattens list or dict objects. Joins each value or item with
        the seperator character. Keys are not included in the joined string.
        When a dict value or a list item is None, no_value_str is used to
        represent that value / item."""
        if value is None:
            return no_value_str

        if isinstance(value, list):
            flattened_values = [self._flatten_values(item, seperator) for item in value]
            return seperator.join(flattened_values)

        elif isinstance(value, dict):
            flattened_values = [self._flatten_values(item, seperator) for item in value.values()]
            return seperator.join(flattened_values)

        else:
            return str(value)

    def _concatenate_dict_fields(self, dictionary, seperator="\n"):
        """Concatenates all values for each key in a dictionary in a nested manner.
        Used to parse a python dictionary to an aggregated string"""
        values = [self._flatten_values(value, seperator) for value in dictionary.values()]
        concatenated_values = seperator.join(values)
        return concatenated_values

    @requires_dependencies(["pyairtable"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process

        self.api = Api(self.config.personal_access_token)
        table = self.api.table(self.file_meta.base_id, self.file_meta.table_id)
        self.document = self._concatenate_dict_fields({"table": table.all()})
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filename, "w", encoding="utf8") as f:
            # import pdb; pdb.set_trace()
            f.write(self.document)


@requires_dependencies(["pyairtable"])
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
        if self.config.list_of_paths:
            self.list_of_paths = self.config.list_of_paths.split()

        self.api = Api(self.config.personal_access_token)

    @requires_dependencies(["pyairtable"])
    def _find_and_assign_base_ids(self):
        self.base_ids = [base["id"] for base in get_api_bases(self.api)["bases"]]

    @requires_dependencies(["pyairtable"])
    def _get_table_ids_within_bases(self):
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
