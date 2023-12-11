import typing as t
import warnings
from dataclasses import dataclass
from urllib.parse import urlparse

from unstructured.ingest.interfaces import BaseSourceConnector
from unstructured.ingest.logger import logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_remote_url

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.fsspec.fsspec import SimpleFsspecConfig


@dataclass
class FsspecRunner(Runner):
    connector_config: "SimpleFsspecConfig"

    def update_read_config(self):
        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="fsspec",
            read_config=self.read_config,
            remote_url=self.fsspec_config.remote_url,  # type: ignore
            logger=logger,
        )

        protocol = urlparse(self.fsspec_config.remote_url).scheme  # type: ignore
        warnings.warn(
            f"`fsspec` protocol {protocol} is not directly supported by `unstructured`,"
            " so use it at your own risk. Supported protocols are `gcs`, `gs`, `s3`, `s3a`,"
            "`dropbox`, `abfs`, `az` and `sftp`.",
            UserWarning,
        )

    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        from unstructured.ingest.connector.fsspec.fsspec import (
            FsspecSourceConnector,
        )

        return FsspecSourceConnector
