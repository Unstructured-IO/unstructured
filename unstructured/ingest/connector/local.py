import fnmatch
import glob
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger


@dataclass
class SimpleLocalConfig(BaseConnectorConfig):
    # Local specific options
    input_path: str
    recursive: bool = False
    file_glob: Optional[str] = None

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

    config: SimpleLocalConfig
    path: str

    @property
    def filename(self):
        """The filename of the local file to be processed"""
        return Path(self.path)

    def cleanup_file(self):
        """Not applicable to local file system"""
        pass

    def get_file(self):
        """Not applicable to local file system"""
        pass

    @property
    def _output_filename(self) -> Path:
        """Returns output filename for the doc
        If input path argument is a file itself, it returns the filename of the doc.
        If input path argument is a folder, it returns the relative path of the doc.
        """
        input_path = Path(self.config.input_path)
        basename = (
            f"{Path(self.path).name}.json"
            if input_path.is_file()
            else f"{Path(self.path).relative_to(input_path)}.json"
        )
        return Path(self.standard_config.output_dir) / basename


class LocalConnector(BaseConnector):
    """Objects of this class support fetching document(s) from local file system"""

    config: SimpleLocalConfig
    ingest_doc_cls: Type[LocalIngestDoc] = LocalIngestDoc

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleLocalConfig,
    ):
        super().__init__(standard_config, config)

    def cleanup(self, cur_dir=None):
        """Not applicable to local file system"""
        pass

    def initialize(self):
        """Not applicable to local file system"""
        pass

    def _list_files(self):
        if self.config.input_path_is_file:
            return glob.glob(f"{self.config.input_path}")
        elif self.config.recursive:
            return glob.glob(f"{self.config.input_path}/**", recursive=self.config.recursive)
        else:
            return glob.glob(f"{self.config.input_path}/*")

    def does_path_match_glob(self, path: str) -> bool:
        if self.config.file_glob is None:
            return True
        patterns = self.config.file_glob.split(",")
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                self.standard_config,
                self.config,
                file,
            )
            for file in self._list_files()
            if os.path.isfile(file) and self.does_path_match_glob(file)
        ]
