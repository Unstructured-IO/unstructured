import glob
import json
import os
import re
from dataclasses import dataclass, field
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
    # Local specific options
    input_dir: str
    recursive: bool = False
    file_glob: Optional[str] = None

    # base connector options
    output_dir: str
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None
    fields_include: str = "element_id,text,type,metadata"


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
            / f"{self.path.replace(f'{self.config.input_dir}/', '')}.json"
        )

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
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
        for file in glob.glob(self.config.input_dir, recursive=self.config.recursive)

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                self.config,
                file,
            )
            for file in self._list_files()
        ]
