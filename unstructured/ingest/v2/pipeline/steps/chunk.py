import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.chunker import Chunker
from unstructured.ingest.v2.logging import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, log_error
from unstructured.staging.base import elements_to_dicts

STEP_ID = "chunk"


class ChunkStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass(kw_only=True)
class ChunkStep(PipelineStep):
    identifier: str = STEP_ID
    process: Chunker

    def should_chunk(self, filepath: Path) -> bool:
        if self.context.reprocess:
            return True
        if not filepath.exists():
            return True
        return False

    def get_output_filepath(self, filename: Path) -> Path:
        hashed_output_file = f"{self.get_hash(extras=[filename.stem])}.json"
        filepath = (self.cache_dir / hashed_output_file).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath

    def _save_output(self, output_filepath: str, chunked_content: list[dict]):
        with open(str(output_filepath), "w") as f:
            logger.debug(f"Writing chunker output to: {output_filepath}")
            json.dump(chunked_content, f, indent=2)

    @log_error()
    def run(self, path: str, file_data_path: str) -> ChunkStepResponse:
        path = Path(path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_chunk(filepath=output_filepath):
            logger.info(f"Skipping chunking, output already exists: {output_filepath}")
            return ChunkStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        chunked_content_raw = self.process.run(elements_filepath=path)
        self._save_output(
            output_filepath=str(output_filepath),
            chunked_content=elements_to_dicts(chunked_content_raw),
        )
        return ChunkStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    async def run_async(self, path: str, file_data_path: str) -> ChunkStepResponse:
        path = Path(path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_chunk(filepath=output_filepath):
            logger.info(f"Skipping chunking, output already exists: {output_filepath}")
            return ChunkStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        chunked_content_raw = await self.process.run_async(elements_filepath=path)
        self._save_output(
            output_filepath=str(output_filepath),
            chunked_content=elements_to_dicts(chunked_content_raw),
        )
        return ChunkStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            self.process.config.to_dict(), sort_keys=True, ensure_ascii=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
