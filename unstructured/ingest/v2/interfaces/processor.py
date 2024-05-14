import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dataclasses_json import DataClassJsonMixin

DEFAULT_WORK_DIR = str((Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve())


@dataclass
class ProcessorConfig(DataClassJsonMixin):
    reprocess: bool = False
    verbose: bool = False
    work_dir: str = field(default_factory=lambda: DEFAULT_WORK_DIR)
    num_processes: int = 2
    raise_on_error: bool = False
    disable_parallelism: bool = field(
        default_factory=lambda: os.getenv("INGEST_DISABLE_PARALLELISM", "false").lower() == "true"
    )
    preserve_downloads: bool = False
    download_only: bool = False
    max_docs: Optional[int] = None
    re_download: bool = False
    uncompress: bool = False
