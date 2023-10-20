import fnmatch
import glob
import os
import typing as t
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
)
from unstructured.ingest.logger import logger


@dataclass
class SimpleLocalConfig(BaseConnectorConfig):
    # Local specific options
    input_path: str
    recursive: bool = False
    file_glob: t.Optional[str] = None

    def __post_init__(self):
        if os.path.isfile(self.input_path):
            self.input_path_is_file = True
        else:
            self.input_path_is_file = False


@dataclass
class LocalIngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    """

    connector_config: SimpleLocalConfig
    path: str
    registry_name: str = "local"

    @property
    def filename(self):
        """The filename of the local file to be processed"""
        return Path(self.path)

    def cleanup_file(self):
        """Not applicable to local file system"""

    def get_file(self):
        """Not applicable to local file system"""

    @property
    def _output_filename(self) -> Path:
        """Returns output filename for the doc
        If input path argument is a file itself, it returns the filename of the doc.
        If input path argument is a folder, it returns the relative path of the doc.
        """
        input_path = Path(self.connector_config.input_path)
        basename = (
            f"{Path(self.path).name}.json"
            if input_path.is_file()
            else f"{Path(self.path).relative_to(input_path)}.json"
        )
        return Path(self.processor_config.output_dir) / basename


@dataclass
class LocalSourceConnector(BaseSourceConnector):
    """Objects of this class support fetching document(s) from local file system"""

    connector_config: SimpleLocalConfig

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[LocalIngestDoc] = LocalIngestDoc

    def cleanup(self, cur_dir=None):
        """Not applicable to local file system"""

    def initialize(self):
        """Not applicable to local file system"""

    def _list_files(self):
        if self.connector_config.input_path_is_file:
            return glob.glob(f"{self.connector_config.input_path}")
        elif self.connector_config.recursive:
            return glob.glob(
                f"{self.connector_config.input_path}/**",
                recursive=self.connector_config.recursive,
            )
        else:
            return glob.glob(f"{self.connector_config.input_path}/*")

    def does_path_match_glob(self, path: str) -> bool:
        if self.connector_config.file_glob is None:
            return True
        patterns = self.connector_config.file_glob.split(",")
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                path=file,
            )
            for file in self._list_files()
            if os.path.isfile(file) and self.does_path_match_glob(file)
        ]
