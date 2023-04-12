import fnmatch
import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.ingest.logger import logger


@dataclass
class SimpleLocalConfig(BaseConnectorConfig):
    output_dir: str

    # Local specific options
    input_path: str
    recursive: bool = False
    file_glob: Optional[str] = None

    # base connector options
    download_only: bool = False
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None
    partition_by_api: bool = False
    partition_endpoint: str = "https://api.unstructured.io/general/v0/general"
    fields_include: str = "element_id,text,type,metadata"
    flatten_metadata: bool = False

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

    def _output_filename(self):
        return (
            Path(self.config.output_dir)
            / f"{self.path.replace(f'{self.config.input_path}/', '')}.json"
        )

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        if self.config.download_only:
            return
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")


class LocalConnector(BaseConnector):
    """Objects of this class support fetching document(s) from local file system"""

    ingest_doc_cls: Type[LocalIngestDoc] = LocalIngestDoc

    def __init__(
        self,
        config: SimpleLocalConfig,
    ):
        self.config = config

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
                self.config,
                file,
            )
            for file in self._list_files()
            if os.path.isfile(file) and self.does_path_match_glob(file)
        ]
