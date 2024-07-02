import os
from asyncio import Semaphore
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin

DEFAULT_WORK_DIR = str((Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve())


@dataclass
class ProcessorConfig(EnhancedDataClassJsonMixin):
    reprocess: bool = False
    verbose: bool = False
    tqdm: bool = False
    work_dir: str = field(default_factory=lambda: DEFAULT_WORK_DIR)
    num_processes: int = 2
    max_connections: Optional[int] = None
    raise_on_error: bool = False
    disable_parallelism: bool = field(
        default_factory=lambda: os.getenv("INGEST_DISABLE_PARALLELISM", "false").lower() == "true"
    )
    preserve_downloads: bool = False
    download_only: bool = False
    max_docs: Optional[int] = None
    re_download: bool = False
    uncompress: bool = False

    # Used to keep track of state in pipeline
    status: dict = field(default_factory=dict)
    semaphore: Optional[Semaphore] = field(init=False, default=None)

    def __post_init__(self):
        if self.max_connections is not None:
            self.semaphore = Semaphore(self.max_connections)

    @property
    def mp_supported(self) -> bool:
        return not self.disable_parallelism and self.num_processes > 1

    @property
    def async_supported(self) -> bool:
        if self.disable_parallelism:
            return False
        if self.max_connections is not None and isinstance(self.max_connections, int):
            return self.max_connections > 1
        return True
