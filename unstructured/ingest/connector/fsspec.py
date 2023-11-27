import json
import os
import typing as t
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from unstructured.ingest.error import (
    DestinationConnectionError,
    SourceConnectionError,
    SourceConnectionNetworkError,
)
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    FsspecConfig,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.compression import (
    TAR_FILE_EXT,
    ZIP_FILE_EXT,
    CompressionSourceConnectorMixin,
)
from unstructured.utils import (
    requires_dependencies,
)

SUPPORTED_REMOTE_FSSPEC_PROTOCOLS = [
    "s3",
    "s3a",
    "abfs",
    "az",
    "gs",
    "gcs",
    "box",
    "dropbox",
]


@dataclass
class SimpleFsspecConfig(FsspecConfig, BaseConnectorConfig):
    pass


@dataclass
class FsspecIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleFsspecConfig
    remote_file_path: str

    def _tmp_download_file(self):
        download_dir = self.read_config.download_dir if self.read_config.download_dir else ""
        return Path(download_dir) / self.remote_file_path.replace(
            f"{self.connector_config.dir_path}/",
            "",
        )

    @property
    def _output_filename(self):
        # Dynamically parse filename , can change if remote path was pointing to the single
        # file, a directory, or nested directory
        if self.remote_file_path == self.connector_config.path_without_protocol:
            file = self.remote_file_path.split("/")[-1]
            filename = f"{file}.json"
        else:
            path_without_protocol = (
                self.connector_config.path_without_protocol
                if self.connector_config.path_without_protocol.endswith("/")
                else f"{self.connector_config.path_without_protocol}/"
            )
            filename = f"{self.remote_file_path.replace(path_without_protocol, '')}.json"
        return Path(self.processor_config.output_dir) / filename

    def _create_full_tmp_dir_path(self):
        """Includes "directories" in the object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the file from the current filesystem and stores it locally."""
        from fsspec import AbstractFileSystem, get_filesystem_class

        self._create_full_tmp_dir_path()
        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        self._get_file(fs=fs)
        fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())
        self.update_source_metadata()

    @SourceConnectionNetworkError.wrap
    def _get_file(self, fs):
        fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())

    @requires_dependencies(["fsspec"])
    def update_source_metadata(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        date_created = None
        with suppress(NotImplementedError):
            date_created = fs.created(self.remote_file_path).isoformat()

        date_modified = None
        with suppress(NotImplementedError):
            date_modified = fs.modified(self.remote_file_path).isoformat()

        version = (
            fs.checksum(self.remote_file_path)
            if self.connector_config.protocol != "gs"
            else fs.info(self.remote_file_path).get("etag", "")
        )
        file_exists = fs.exists(self.remote_file_path)
        self.source_metadata = SourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            version=version,
            source_url=f"{self.connector_config.protocol}://{self.remote_file_path}",
            exists=file_exists,
        )

    @property
    def filename(self):
        """The filename of the file after downloading from cloud"""
        return self._tmp_download_file()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        """Returns the equivalent of ls in dict"""
        return {
            "protocol": self.connector_config.protocol,
            "remote_file_path": self.remote_file_path,
        }


@dataclass
class FsspecSourceConnector(
    SourceConnectorCleanupMixin,
    CompressionSourceConnectorMixin,
    BaseSourceConnector,
):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleFsspecConfig

    def check_connection(self):
        from fsspec import get_filesystem_class

        try:
            fs = get_filesystem_class(self.connector_config.protocol)(
                **self.connector_config.get_access_kwargs(),
            )
            fs.ls(path=self.connector_config.path_without_protocol)
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[FsspecIngestDoc] = FsspecIngestDoc

    def initialize(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        """Verify that can get metadata for an object, validates connections info."""
        ls_output = self.fs.ls(self.connector_config.path_without_protocol)
        if len(ls_output) < 1:
            raise ValueError(
                f"No objects found in {self.connector_config.remote_url}.",
            )

    def _list_files(self):
        if not self.connector_config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems
            # because they are seen as 0 byte files
            return [
                x.get("name")
                for x in self.fs.ls(self.connector_config.path_without_protocol, detail=True)
                if x.get("size") > 0
            ]
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            return [
                k
                for k, v in self.fs.find(
                    self.connector_config.path_without_protocol,
                    detail=True,
                ).items()
                if v.get("size") > 0
            ]

    def get_ingest_docs(self):
        files = self._list_files()
        # remove compressed files
        compressed_file_ext = TAR_FILE_EXT + ZIP_FILE_EXT
        compressed_files = []
        uncompressed_files = []
        docs: t.List[BaseSingleIngestDoc] = []
        for file in files:
            if any(file.endswith(ext) for ext in compressed_file_ext):
                compressed_files.append(file)
            else:
                uncompressed_files.append(file)
        docs.extend(
            [
                self.ingest_doc_cls(
                    read_config=self.read_config,
                    connector_config=self.connector_config,
                    processor_config=self.processor_config,
                    remote_file_path=file,
                )
                for file in uncompressed_files
            ],
        )
        if not self.connector_config.uncompress:
            return docs
        for compressed_file in compressed_files:
            compressed_doc = self.ingest_doc_cls(
                read_config=self.read_config,
                processor_config=self.processor_config,
                connector_config=self.connector_config,
                remote_file_path=compressed_file,
            )
            try:
                local_ingest_docs = self.process_compressed_doc(doc=compressed_doc)
                logger.info(f"adding {len(local_ingest_docs)} from {compressed_file}")
                docs.extend(local_ingest_docs)
            finally:
                compressed_doc.cleanup_file()
        return docs


@dataclass
class FsspecWriteConfig(WriteConfig):
    write_text_kwargs: t.Dict[str, t.Any] = field(default_factory=dict)


@dataclass
class FsspecDestinationConnector(BaseDestinationConnector):
    connector_config: SimpleFsspecConfig
    write_config: FsspecWriteConfig

    def initialize(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

    def check_connection(self):
        from fsspec import get_filesystem_class

        try:
            fs = get_filesystem_class(self.connector_config.protocol)(
                **self.connector_config.get_access_kwargs(),
            )
            fs.ls(path=self.connector_config.path_without_protocol)
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def write_dict(
        self,
        *args,
        elements_dict: t.List[t.Dict[str, t.Any]],
        filename: t.Optional[str] = None,
        indent: int = 4,
        encoding: str = "utf-8",
        **kwargs,
    ) -> None:
        from fsspec import AbstractFileSystem, get_filesystem_class

        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        logger.info(f"Writing content using filesystem: {type(fs).__name__}")

        output_folder = self.connector_config.path_without_protocol
        output_folder = os.path.join(output_folder)  # Make sure folder ends with file seperator
        filename = (
            filename.strip(os.sep) if filename else filename
        )  # Make sure filename doesn't begin with file seperator
        output_path = str(PurePath(output_folder, filename)) if filename else output_folder
        full_output_path = f"{self.connector_config.protocol}://{output_path}"
        logger.debug(f"uploading content to {full_output_path}")
        fs.write_text(
            full_output_path,
            json.dumps(elements_dict, indent=indent),
            encoding=encoding,
            **self.write_config.write_text_kwargs,
        )

    def write(self, docs: t.List[BaseSingleIngestDoc]) -> None:
        for doc in docs:
            file_path = doc.base_output_filename
            filename = file_path if file_path else None
            with open(doc._output_filename) as json_file:
                logger.debug(f"uploading content from {doc._output_filename}")
                json_list = json.load(json_file)
                self.write_dict(elements_dict=json_list, filename=filename)
