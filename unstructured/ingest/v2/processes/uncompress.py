from abc import ABC
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.utils.compression import TAR_FILE_EXT, ZIP_FILE_EXT, uncompress_file
from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class UncompressConfig(EnhancedDataClassJsonMixin):
    pass


@dataclass
class Uncompressor(BaseProcess, ABC):
    config: UncompressConfig = field(default_factory=UncompressConfig)

    def is_async(self) -> bool:
        return True

    def run(self, file_data: FileData, **kwargs: Any) -> list[FileData]:
        local_filepath = Path(file_data.source_identifiers.fullpath)
        if local_filepath.suffix not in TAR_FILE_EXT + ZIP_FILE_EXT:
            return [file_data]
        new_path = uncompress_file(filename=str(local_filepath))
        new_files = [i for i in Path(new_path).rglob("*") if i.is_file()]
        responses = []
        for f in new_files:
            new_file_data = copy(file_data)
            new_file_data.source_identifiers.fullpath = str(f)
            if new_file_data.source_identifiers.rel_path:
                new_file_data.source_identifiers.rel_path = str(f).replace(
                    str(local_filepath.parent), ""
                )[1:]
            responses.append(new_file_data)
        return responses

    async def run_async(self, file_data: FileData, **kwargs: Any) -> list[FileData]:
        return self.run(file_data=file_data, **kwargs)
