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
    list_of_paths: Optional[str]


@dataclass
class AirtableFileMeta:
    """Metadata specifying a table id, a base id which the table is stored in,
    and an optional view id in case particular rows and fields are to be ingested"""

    base_id: str
    table_id: str
    view_id: Optional[str] = None


@dataclass
class AirtableIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates an Airtable connection object
    to fetch each document, rather than creating a it for each thread.
    """

    config: SimpleAirtableConfig
    file_meta: AirtableFileMeta
    registry_name: str = "airtable"

    @property
    def filename(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.base_id
            / f"{self.file_meta.table_id}.csv"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, base id, and table id"""
        output_file = f"{self.file_meta.table_id}.json"
        return Path(self.standard_config.output_dir) / self.file_meta.base_id / output_file

    @requires_dependencies(["pyairtable", "pandas"], extras="airtable")
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process
        import pandas as pd
        from pyairtable import Api

        self.api = Api(self.config.personal_access_token)
        table = self.api.table(self.file_meta.base_id, self.file_meta.table_id)

        df = pd.DataFrame.from_dict(
            [row["fields"] for row in table.all(view=self.file_meta.view_id)],
        ).sort_index(axis=1)

        self.document = df.to_csv()
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


airtable_id_prefixes = ["app", "tbl", "viw"]


def raise_airtable_path_error(piece):
    if any(piece[:3] == prefix for prefix in airtable_id_prefixes):
        raise (
            ValueError(
                "Path components are not correctly ordered.\
                            Valid path structures: \
                            - base_id/table_id/view_id , \
                            - base_id/table_id, \
                            - base_id .\
                            It is also possible to leave --airtable-list-of-paths \
                            argument empty (this will ingest everything).",
            )
        )
    else:
        raise (
            ValueError(
                """Path components are not valid Airtable ids.
                        base_id should look like: appAbcDeF1ghijKlm,
                        table_id should look like: tblAbcDeF1ghijKlm,
                        view_id should look like:  viwAbcDeF1ghijKlm""",
            )
        )


def check_path_validity(path):
    pieces = path.split("/")
    assert (
        1 <= len(pieces) <= 3
    ), "Path should be composed of between 1-3 \
                                components (base_id, table_id, view_id)."

    for i, piece in enumerate(pieces):
        try:
            assert piece[:3] == airtable_id_prefixes[i]
        except AssertionError:
            raise_airtable_path_error(piece)


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

    @requires_dependencies(["pyairtable"], extras="airtable")
    def initialize(self):
        from pyairtable import Api

        self.base_ids_to_fetch_tables_from = []
        if self.config.list_of_paths:
            self.list_of_paths = self.config.list_of_paths.split()

        self.api = Api(self.config.personal_access_token)

    @requires_dependencies(["pyairtable"], extras="airtable")
    def use_all_bases(self):
        from pyairtable.metadata import get_api_bases

        self.base_ids_to_fetch_tables_from = [
            base["id"] for base in get_api_bases(self.api)["bases"]
        ]

    @requires_dependencies(["pyairtable"], extras="airtable")
    def fetch_table_ids(self):
        from pyairtable.metadata import get_base_schema

        bases = [
            (base_id, self.api.base(base_id)) for base_id in self.base_ids_to_fetch_tables_from
        ]

        metadata_for_each_base = [
            (base_id, get_base_schema(base)["tables"]) for base_id, base in bases
        ]

        baseid_tableid_viewid_tuples = [
            (base_id, table["id"], None)
            for base_id, base_metadata in metadata_for_each_base
            for table in base_metadata
        ]

        return baseid_tableid_viewid_tuples

    def get_ingest_docs(self):
        """Fetches documents in an Airtable org."""

        # When no list of paths provided, the connector ingests everything.
        if not self.config.list_of_paths:
            self.use_all_bases()
            baseid_tableid_viewid_tuples = self.fetch_table_ids()

        # When there is a list of paths, the connector checks the validity
        # of the paths, and fetches table_ids to be ingested, based on the paths.
        else:
            self.paths = self.config.list_of_paths.split()
            self.paths = [path.strip("/") for path in self.paths]

            [check_path_validity(path) for path in self.paths]

            self.base_ids_to_fetch_tables_from = []
            baseid_tableid_viewid_tuples = []

            for path in self.paths:
                components = path.split("/")
                if len(components) == 1:  # only a base_id is provided
                    self.base_ids_to_fetch_tables_from.append(components[0])
                elif len(components) == 2:  # a base_id and a table_id are provided
                    baseid_tableid_viewid_tuples.append((components[0], components[1], None))
                elif len(components) == 3:  # a base_id, table_id, and a view_id are provided
                    baseid_tableid_viewid_tuples.append(
                        (components[0], components[1], components[2]),
                    )

            baseid_tableid_viewid_tuples += self.fetch_table_ids()

        return [
            AirtableIngestDoc(
                self.standard_config,
                self.config,
                AirtableFileMeta(base_id, table_id, view_id),
            )
            for base_id, table_id, view_id in baseid_tableid_viewid_tuples
        ]
