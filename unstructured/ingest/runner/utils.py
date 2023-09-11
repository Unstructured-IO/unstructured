from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from unstructured.ingest.interfaces import (
    ReadConfig,
)


def update_download_dir_remote_url(
    connector_name: str,
    read_config: ReadConfig,
    remote_url: str,
    logger: logging.Logger,
) -> str:
    hashed_dir_name = hashlib.sha256(remote_url.encode("utf-8"))
    return update_download_dir_hash(
        connector_name=connector_name,
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )


def update_download_dir_hash(
    connector_name: str,
    read_config: ReadConfig,
    hashed_dir_name: hashlib._Hash,
    logger: logging.Logger,
) -> str:
    if not read_config.download_dir:
        cache_path = Path.home() / ".cache" / "unstructured" / "ingest"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
        download_dir = cache_path / connector_name / hashed_dir_name.hexdigest()[:10]
        if read_config.preserve_downloads:
            logger.warning(
                f"Preserving downloaded files but download_dir is not specified,"
                f" using {download_dir}",
            )
        new_download_dir = str(download_dir)
        logger.debug(f"updating download directory to: {new_download_dir}")
    else:
        new_download_dir = read_config.download_dir
    return new_download_dir
