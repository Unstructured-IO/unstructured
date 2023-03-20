import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from ftplib import FTP, error_perm
from pathlib import Path
from typing import List, Optional, Union

import requests
from bs4 import BeautifulSoup

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.ingest.logger import logger

DOMAIN = "ftp.ncbi.nlm.nih.gov"
FTP_DOMAIN = f"ftp://{DOMAIN}"
PMC_DIR = "pub/pmc"
PDF_DIR = "oa_pdf"


@dataclass
class BiomedFileMeta:
    ftp_path: str
    download_filepath: Union[str, os.PathLike]
    output_filepath: Union[str, os.PathLike]


@dataclass
class SimpleBiomedConfig(BaseConnectorConfig):
    """Connector config where path is the FTP directory path and
    id_, from_, until, format are API parameters."""

    path: str

    # OA Web Service API Options
    id_: str
    from_: str
    until: str

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching FTP path
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None

    def _validate_date_args(self, date):
        date_formats = ["%Y-%m-%d", "%Y-%m-%d+%H:%M:%S"]

        valid = False
        if date:
            date = date.replace(" ", "+").replace("%20", "+")
            for format in date_formats:
                try:
                    datetime.strptime(date, format)
                    valid = True
                    break
                except ValueError:
                    pass

            if not valid:
                raise ValueError(
                    f"The from argument {date} does not satisfy the format: "
                    "YYYY-MM-DD or YYYY-MM-DD HH:MM:SS",
                )

        return valid

    def validate_api_inputs(self):
        valid = False

        if self.from_:
            valid = self._validate_date_args(self.from_)

        if self.until:
            valid = self._validate_date_args(self.until)

        return valid

    def __post_init__(self):
        self.is_file = False
        self.is_dir = False
        self.is_api = False

        if not self.path:
            is_valid = self.validate_api_inputs()
            if not is_valid:
                raise ValueError(
                    "Path argument or atleast one of the "
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
                    raise ValueError("Something went wrong when validating the path: {path}.")


@dataclass
class BiomedIngestDoc(BaseIngestDoc):
    config: SimpleBiomedConfig
    file_meta: BiomedFileMeta

    @property
    def filename(self):
        return Path(self.file_meta.download_filepath).resolve()  # type: ignore

    def _output_filename(self):
        return Path(f"{self.file_meta.output_filepath}.json").resolve()

    def cleanup_file(self):
        if not self.config.preserve_downloads and self.filename.is_file():
            logger.debug(f"Cleaning up {self}")
            Path.unlink(self.filename)

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

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

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")


class BiomedConnector(BaseConnector):
    """Objects of this class support fetching documents from Biomedical literature FTP directory"""

    def __init__(self, config):
        self.config = config
        self.cleanup_files = not self.config.preserve_downloads

    def _list_objects_api(self):
        def urls_to_metadata(urls):
            files = []
            for url in urls:
                parts = url.split(PDF_DIR)
                if len(parts) > 1:
                    local_path = parts[1].strip("/")
                    files.append(
                        BiomedFileMeta(
                            ftp_path=url,
                            download_filepath=(
                                Path(self.config.download_dir) / local_path
                            ).resolve(),
                            output_filepath=(Path(self.config.output_dir) / local_path).resolve(),
                        ),
                    )

            return files

        files: List[BiomedFileMeta] = []

        endpoint_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?format=pdf"

        if self.config.id_:
            endpoint_url += f"&id={self.config.id_}"

        if self.config.from_:
            endpoint_url += f"&from={self.config.from_}"

        if self.config.until:
            endpoint_url += f"&until={self.config.until}"

        while endpoint_url:
            response = requests.get(endpoint_url)
            soup = BeautifulSoup(response.content, features="lxml")
            urls = [link["href"] for link in soup.find_all("link")]

            if not urls:
                return files

            endpoint_url = urls[-1] if "resumptiontoken" in urls[-1].lower() else None
            if endpoint_url:
                urls = urls[:-1]

            files.extend(urls_to_metadata(urls))

        return files

    def _list_objects(self):
        files = []

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
                                download_filepath=(
                                    Path(self.config.download_dir) / local_path
                                ).resolve(),
                                output_filepath=(
                                    Path(self.config.output_dir) / local_path
                                ).resolve(),
                            ),
                        )

                else:
                    for sub_path in sub_paths:
                        traverse(sub_path, download_dir, output_dir)

            else:
                raise ValueError(f"{full_path} is not a valid directory.")

        ftp_path = f"{FTP_DOMAIN}/{PMC_DIR}/{self.config.path}"
        if self.config.is_file:
            local_path = "/".join(self.config.path.split("/")[1:])
            return [
                BiomedFileMeta(
                    ftp_path=ftp_path,
                    download_filepath=(Path(self.config.download_dir) / local_path).resolve(),
                    output_filepath=(Path(self.config.output_dir) / local_path).resolve(),
                ),
            ]
        else:
            traverse(
                Path(self.config.path),
                Path(self.config.download_dir),
                Path(self.config.output_dir),
            )

        return files

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir

        if cur_dir is None or not Path(cur_dir).is_dir():
            return

        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)

    def initialize(self):
        pass

    def get_ingest_docs(self):
        files = self._list_objects_api() if self.config.is_api else self._list_objects()
        return [BiomedIngestDoc(self.config, file) for file in files]
