import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict
from unstructured.ingest.v2.processes.embedder import Embedder
from unstructured.staging.base import elements_to_dicts

STEP_ID = "embed"


class EmbedStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass
class EmbedStep(PipelineStep):
    process: Embedder
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.config.embedding_provider})"

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.config.to_dict(redact_sensitive=True))
            if self.process.config
            else None
        )
        logger.info(f"Starting {self.identifier} with configs: {config}")

    def should_embed(self, filepath: Path, file_data: FileData) -> bool:
        if self.context.reprocess or file_data.reprocess:
            return True
        if not filepath.exists():
            return True
        return False

    def get_output_filepath(self, filename: Path) -> Path:
        hashed_output_file = f"{self.get_hash(extras=[filename.name])}.json"
        filepath = (self.cache_dir / hashed_output_file).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath

    def _save_output(self, output_filepath: str, embedded_content: list[dict]):
        with open(str(output_filepath), "w") as f:
            logger.debug(f"Writing embedded output to: {output_filepath}")
            json.dump(embedded_content, f, indent=2)

    async def _run_async(self, fn: Callable, path: str, file_data_path: str) -> EmbedStepResponse:
        path = Path(path)
        file_data = FileData.from_file(path=file_data_path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_embed(filepath=output_filepath, file_data=file_data):
            logger.debug(f"Skipping embedding, output already exists: {output_filepath}")
            return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        fn_kwargs = {"elements_filepath": path}
        if not asyncio.iscoroutinefunction(fn):
            embed_content_raw = fn(**fn_kwargs)
        elif semaphore := self.context.semaphore:
            async with semaphore:
                embed_content_raw = await fn(**fn_kwargs)
        else:
            embed_content_raw = await fn(**fn_kwargs)

        self._save_output(
            output_filepath=str(output_filepath),
            embedded_content=elements_to_dicts(embed_content_raw),
        )
        return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            self.process.config.to_dict(), sort_keys=True, ensure_ascii=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
