import fnmatch
import glob
import os
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

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
    uncompress: bool = False

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
    is_compressed: bool = False
    children: List["BaseIngestDoc"] = field(default_factory=list)

    def get_children(self) -> List["BaseIngestDoc"]:
        return self.children

    def process_file(self, **partition_kwargs) -> Optional[List[Dict[str, Any]]]:
        if self.is_compressed:
            self.config.get_logger().warning(
                f"file detected as zip, skipping process file: {self.filename}",
            )
            return None
        return super().process_file(**partition_kwargs)

    def write_result(self):
        if self.is_compressed:
            self.config.get_logger().warning(
                f"file detected as zip, skipping write results: {self.filename}",
            )
            return None
        return super().write_result()

    @property
    def filename(self):
        """The filename of the local file to be processed"""
        return Path(self.path)

    def cleanup_file(self):
        """Not applicable to local file system"""
        pass

    def get_file(self):
        # Check if file is compressed
        # The way zipfile.is_zipfile() check the file, it can mistake .pptx files as zip.
        # Adding the extension check to be extra sure.
        file_extension = os.path.splitext(self.path)[-1]
        if zipfile.is_zipfile(self.path) and file_extension == ".zip":
            self.is_compressed = True
            if self.config.uncompress:
                self.process_zip(zip_path=self.path)
        if tarfile.is_tarfile(self.path):
            self.is_compressed = True
            if self.config.uncompress:
                self.process_tar(tar_path=self.path)

    def process_zip(self, zip_path: str):
        head, tail = os.path.split(zip_path)
        path = os.path.join(head, f"{tail}-zip-uncompressed")
        self.config.get_logger().info(f"extracting zip {zip_path} -> {path}")
        with zipfile.ZipFile(zip_path) as zfile:
            zfile.extractall(path=path)
        local_connector = LocalConnector(
            standard_config=StandardConnectorConfig(**self.standard_config.__dict__),
            config=SimpleLocalConfig(
                input_path=path,
                recursive=True,
            ),
        )
        self.children.extend(local_connector.get_ingest_docs())

    def process_tar(self, tar_path: str):
        head, tail = os.path.split(tar_path)
        path = os.path.join(head, f"{tail}-tar-uncompressed")
        self.config.get_logger().info(f"extracting tar {tar_path} -> {path}")
        try:
            with tarfile.TarFile(tar_path) as tfile:
                tfile.extractall(path=path)
        except tarfile.ReadError as read_error:
            self.config.get_logger().error(f"failed to uncompress tar {tar_path}: {read_error}")
            return
        local_connector = LocalConnector(
            standard_config=StandardConnectorConfig(**self.standard_config.__dict__),
            config=SimpleLocalConfig(
                input_path=path,
                recursive=True,
            ),
        )
        self.children.extend(local_connector.get_ingest_docs())

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
