import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ProcessorConfig:
    reprocess: bool = False
    verbose: bool = False
    work_dir: str = field(
        default_factory=lambda: str(
            (Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve()
        )
    )
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
