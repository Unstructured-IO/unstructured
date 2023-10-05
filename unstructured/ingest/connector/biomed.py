import os
import typing as t
import urllib.request
from dataclasses import dataclass
from ftplib import FTP, error_perm
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    validate_date_args,
)

DOMAIN = "ftp.ncbi.nlm.nih.gov"
FTP_DOMAIN = f"ftp://{DOMAIN}"
PMC_DIR = "pub/pmc"
PDF_DIR = "oa_pdf"


@dataclass
class BiomedFileMeta:
    ftp_path: str
    download_filepath: str
    output_filepath: str


@dataclass
class SimpleBiomedConfig(BaseConnectorConfig):
    """Connector config where path is the FTP directory path and
    id_, from_, until, format are API parameters."""

    path: t.Optional[str]
    # OA Web Service API Options
    id_: t.Optional[str]
    from_: t.Optional[str]
    until: t.Optional[str]
    max_retries: int = 5
    request_timeout: int = 45
    decay: float = 0.3

    def validate_api_inputs(self):
        valid = False

        if self.from_:
            valid = validate_date_args(self.from_)

        if self.until:
            valid = validate_date_args(self.until)

        return valid

    def __post_init__(self):
        self.is_file = False
        self.is_dir = False
        self.is_api = False

        if not self.path:
            is_valid = self.validate_api_inputs()
            if not is_valid:
                raise ValueError(
                    "Path argument or at least one of the "
                    "OA Web Service arguments MUST be provided.",
                )

            self.is_api = True
        else:
            self.path = self.path.strip("/")
            is_valid = self.path.lower().startswith(PDF_DIR)

            if not is_valid:
                raise ValueError(f"Path MUST start with {PDF_DIR}")

            ftp = FTP(DOMAIN)
            ftp.login()

            path = Path(PMC_DIR) / self.path
            response = ""
            try:
                if path.suffix == ".pdf":
                    response = ftp.cwd(str(path.parent))
                    self.is_file = True
                else:
                    response = ftp.cwd(str(path))
            except error_perm as exc:
                if "no such file or directory" in exc.args[0].lower():
                    raise ValueError(f"The path: {path} is not valid.")
                elif "not a directory" in exc.args[0].lower():
                    self.is_file = True
                elif "command successful" in response:
                    self.is_dir = True
                else:
                    raise ValueError(
                        "Something went wrong when validating the path: {path}.",
                    )


@dataclass
class BiomedIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleBiomedConfig
    file_meta: BiomedFileMeta
    registry_name: str = "biomed"

    @property
    def filename(self):
        return Path(self.file_meta.download_filepath).resolve()  # type: ignore

    @property
    def _output_filename(self):
        return Path(f"{self.file_meta.output_filepath}.json").resolve()

    def cleanup_file(self):
        if (
            not self.read_config.preserve_downloads
            and self.filename.is_file()
            and not self.read_config.download_only
        ):
            logger.debug(f"Cleaning up {self}")
            Path.unlink(self.filename)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        download_path = self.file_meta.download_filepath  # type: ignore
        dir_ = Path(os.path.dirname(download_path))  # type: ignore
        if not dir_.is_dir():
            logger.debug(f"Creating directory: {dir_}")

            if dir_:
                dir_.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(
            self.file_meta.ftp_path,  # type: ignore
            self.file_meta.download_filepath,
        )
        logger.debug(f"File downloaded: {self.file_meta.download_filepath}")


class BiomedSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching documents from Biomedical literature FTP directory"""

    connector_config: SimpleBiomedConfig

    def _list_objects_api(self) -> t.List[BiomedFileMeta]:
        def urls_to_metadata(urls):
            files = []
            for url in urls:
                parts = url.split(PDF_DIR)
                if len(parts) > 1:
                    local_path = parts[1].strip("/")
                    files.append(
                        BiomedFileMeta(
                            ftp_path=url,
                            download_filepath=(Path(self.read_config.download_dir) / local_path)
                            .resolve()
                            .as_posix(),
                            output_filepath=(Path(self.partition_config.output_dir) / local_path)
                            .resolve()
                            .as_posix(),
                        ),
                    )

            return files

        files: t.List[BiomedFileMeta] = []

        endpoint_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?format=pdf"

        if self.connector_config.id_:
            endpoint_url += f"&id={self.connector_config.id_}"

        if self.connector_config.from_:
            endpoint_url += f"&from={self.connector_config.from_}"

        if self.connector_config.until:
            endpoint_url += f"&until={self.connector_config.until}"

        while endpoint_url:
            session = requests.Session()
            retries = Retry(
                total=self.connector_config.max_retries,
                backoff_factor=self.connector_config.decay,
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            response = session.get(endpoint_url, timeout=self.connector_config.request_timeout)
            soup = BeautifulSoup(response.content, features="lxml")
            urls = [link["href"] for link in soup.find_all("link")]

            if not urls:
                return files

            endpoint_url = urls[-1] if "resumptiontoken" in urls[-1].lower() else None
            if endpoint_url:
                urls = urls[:-1]

            files.extend(urls_to_metadata(urls))

        return files

    def _list_objects(self) -> t.List[BiomedFileMeta]:
        files = []

        # Conform to mypy, null check performed elsewhere.
        # Wouldn't be in this method unless self.config.path exists
        path: str = self.connector_config.path if self.connector_config.path else ""

        def traverse(path, download_dir, output_dir):
            full_path = Path(PMC_DIR) / path
            logger.debug(f"Traversing directory: {full_path}")

            ftp = FTP(DOMAIN)
            ftp.login()

            try:
                response = ftp.cwd(str(full_path))
            except error_perm:
                raise ValueError(f"{full_path} is not a valid directory.")

            if "command successful" in response.lower():
                sub_paths = [path / p for p in ftp.nlst()]

                if not sub_paths:
                    return

                ext = Path(sub_paths[0]).suffix
                if ext:
                    for sub_path in sub_paths:
                        ftp_path = f"{FTP_DOMAIN}/{PMC_DIR}/{sub_path}"
                        local_path = "/".join(str(sub_path).split("/")[1:])
                        files.append(
                            BiomedFileMeta(
                                ftp_path=ftp_path,
                                download_filepath=(Path(self.read_config.download_dir) / local_path)
                                .resolve()
                                .as_posix(),
                                output_filepath=(
                                    Path(self.partition_config.output_dir) / local_path
                                )
                                .resolve()
                                .as_posix(),
                            ),
                        )

                else:
                    for sub_path in sub_paths:
                        traverse(sub_path, download_dir, output_dir)

            else:
                raise ValueError(f"{full_path} is not a valid directory.")

        ftp_path = f"{FTP_DOMAIN}/{PMC_DIR}/{self.connector_config.path}"
        if self.connector_config.is_file:
            local_path = "/".join(path.split("/")[1:])
            return [
                BiomedFileMeta(
                    ftp_path=ftp_path,
                    download_filepath=(Path(self.read_config.download_dir) / local_path)
                    .resolve()
                    .as_posix(),
                    output_filepath=(Path(self.partition_config.output_dir) / local_path)
                    .resolve()
                    .as_posix(),
                ),
            ]
        else:
            traverse(
                Path(path),
                Path(self.read_config.download_dir),
                Path(self.partition_config.output_dir),
            )

        return files

    def initialize(self):
        pass

    def get_ingest_docs(self):
        files = self._list_objects_api() if self.connector_config.is_api else self._list_objects()
        return [
            BiomedIngestDoc(
                connector_config=self.connector_config,
                read_config=self.read_config,
                partition_config=self.partition_config,
                file_meta=file,
            )
            for file in files
        ]
