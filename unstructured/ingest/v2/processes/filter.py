import fnmatch
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess
from unstructured.ingest.v2.logger import logger


@dataclass
class FiltererConfig(EnhancedDataClassJsonMixin):
    file_glob: Optional[list[str]] = None
    max_file_size: Optional[int] = None


@dataclass
class Filterer(BaseProcess, ABC):
    config: FiltererConfig = field(default_factory=lambda: FiltererConfig())
    filters: list[Callable[[FileData], bool]] = field(init=False, default_factory=list)

    def __post_init__(self):
        # Populate the filters based on values in config
        if self.config.file_glob is not None:
            self.filters.append(self.glob_filter)
        if self.config.max_file_size:
            self.filters.append(self.file_size_filter)

    def is_async(self) -> bool:
        return False

    def file_size_filter(self, file_data: FileData) -> bool:
        if filesize_bytes := file_data.metadata.filesize_bytes:
            return filesize_bytes <= self.config.max_file_size
        return True

    def glob_filter(self, file_data: FileData) -> bool:
        patterns = self.config.file_glob
        path = file_data.source_identifiers.fullpath
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False

    def run(self, file_data: FileData, **kwargs: Any) -> Optional[FileData]:
        for filter in self.filters:
            if not filter(file_data):
                logger.debug(
                    f"filtered out file data due to {filter.__name__}: {file_data.identifier}"
                )
                return None
        return file_data
