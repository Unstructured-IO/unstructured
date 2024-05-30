import copy
import os
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from unstructured.ingest.connector.local import LocalSourceConnector, SimpleLocalConfig
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.logger import logger

ZIP_FILE_EXT = [".zip"]
TAR_FILE_EXT = [".tar", ".tar.gz", ".tgz"]


def uncompress_file(filename: str, path: Optional[str] = None) -> str:
    """
    Takes in a compressed zip or tar file and uncompresses it
    """
    # Create path if it doesn't already exist
    if path:
        Path(path).mkdir(parents=True, exist_ok=True)

    if any(filename.endswith(ext) for ext in ZIP_FILE_EXT):
        return uncompress_zip_file(zip_filename=filename, path=path)
    elif any(filename.endswith(ext) for ext in TAR_FILE_EXT):
        return uncompress_tar_file(tar_filename=filename, path=path)
    else:
        raise ValueError(
            "filename {} not a recognized compressed extension: {}".format(
                filename,
                ", ".join(ZIP_FILE_EXT + TAR_FILE_EXT),
            ),
        )


def uncompress_zip_file(zip_filename: str, path: Optional[str] = None) -> str:
    head, tail = os.path.split(zip_filename)
    for ext in ZIP_FILE_EXT:
        if tail.endswith(ext):
            tail = tail[: -(len(ext))]
            break
    path = path if path else os.path.join(head, f"{tail}-zip-uncompressed")
    logger.info(f"extracting zip {zip_filename} -> {path}")
    with zipfile.ZipFile(zip_filename) as zfile:
        zfile.extractall(path=path)
    return path


def uncompress_tar_file(tar_filename: str, path: Optional[str] = None) -> str:
    head, tail = os.path.split(tar_filename)
    for ext in TAR_FILE_EXT:
        if tail.endswith(ext):
            tail = tail[: -(len(ext))]
            break

    path = path if path else os.path.join(head, f"{tail}-tar-uncompressed")
    logger.info(f"extracting tar {tar_filename} -> {path}")
    with tarfile.open(tar_filename, "r:gz") as tfile:
        # NOTE(robinson: Mitigate against malicious content being extracted from the tar file.
        # This was added in Python 3.12
        # Ref: https://docs.python.org/3/library/tarfile.html#extraction-filters
        if sys.version_info >= (3, 12):
            tfile.extraction_filter = tarfile.tar_filter
        else:
            logger.warning(
                "Extraction filtering for tar files is available for Python 3.12 and above. "
                "Consider upgrading your Python version to improve security. "
                "See https://docs.python.org/3/library/tarfile.html#extraction-filters"
            )
        tfile.extractall(path=path)
    return path


@dataclass
class CompressionSourceConnectorMixin:
    processor_config: ProcessorConfig
    read_config: ReadConfig
    connector_config: BaseConnectorConfig

    def process_compressed_doc(self, doc: BaseSingleIngestDoc) -> List[BaseSingleIngestDoc]:
        """
        Utility function which helps process compressed files. Extracts the contents and returns
        generated ingest docs via local source connector
        """
        # Download the raw file to local
        doc.get_file()
        path = uncompress_file(filename=str(doc.filename))
        new_read_configs = copy.copy(self.read_config)
        new_process_configs = copy.copy(self.processor_config)
        relative_path = path.replace(self.read_config.download_dir, "")

        if self.processor_config.output_dir.endswith(os.sep):
            new_process_configs.output_dir = f"{self.processor_config.output_dir}{relative_path}"
        else:
            new_process_configs.output_dir = (
                f"{self.processor_config.output_dir}{os.sep}{relative_path}"
            )

        local_connector = LocalSourceConnector(
            connector_config=SimpleLocalConfig(
                input_path=path,
                recursive=True,
            ),
            read_config=new_read_configs,
            processor_config=new_process_configs,
        )
        logger.info(f"Created local source connector: {local_connector.to_json()}")
        local_connector.initialize()
        return local_connector.get_ingest_docs()
