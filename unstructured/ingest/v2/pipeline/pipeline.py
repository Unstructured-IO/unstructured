import logging
import multiprocessing as mp
from dataclasses import InitVar, dataclass, field
from typing import Any, Optional, Union

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.steps.chunk import Chunker, ChunkStep
from unstructured.ingest.v2.pipeline.steps.download import DownloaderT, DownloadStep
from unstructured.ingest.v2.pipeline.steps.embed import Embedder, EmbedStep
from unstructured.ingest.v2.pipeline.steps.index import IndexerT, IndexStep
from unstructured.ingest.v2.pipeline.steps.partition import Partitioner, PartitionStep
from unstructured.ingest.v2.pipeline.steps.stage import UploadStager, UploadStageStep
from unstructured.ingest.v2.pipeline.steps.uncompress import Uncompressor, UncompressStep
from unstructured.ingest.v2.pipeline.steps.upload import Uploader, UploadStep
from unstructured.ingest.v2.processes.connectors.local import LocalUploader


@dataclass
class Pipeline:
    context: ProcessorConfig
    indexer: InitVar[IndexerT]
    indexer_step: IndexStep = field(init=False)
    downloader: InitVar[DownloaderT]
    downloader_step: DownloadStep = field(init=False)
    partitioner: InitVar[Partitioner]
    partitioner_step: PartitionStep = field(init=False)
    chunker: InitVar[Chunker] = None
    chunker_step: ChunkStep = field(init=False, default=None)
    embedder: InitVar[Embedder] = None
    embedder_step: EmbedStep = field(init=False, default=None)
    stager: InitVar[UploadStager] = None
    stager_step: UploadStageStep = field(init=False, default=None)
    uploader: InitVar[Uploader] = field(default=LocalUploader)
    uploader_step: UploadStep = field(init=False, default=None)
    uncompress_step: UncompressStep = field(init=False, default=None)

    def __post_init__(
        self,
        indexer: IndexerT,
        downloader: DownloaderT,
        partitioner: Partitioner,
        chunker: Chunker = None,
        embedder: Embedder = None,
        stager: UploadStager = None,
        uploader: Uploader = None,
    ):
        logger.setLevel(level=logging.DEBUG if self.context.verbose else logging.INFO)
        self.indexer_step = IndexStep(process=indexer, context=self.context)
        self.downloader_step = DownloadStep(process=downloader, context=self.context)
        self.partitioner_step = PartitionStep(process=partitioner, context=self.context)
        self.chunker_step = ChunkStep(process=chunker, context=self.context) if chunker else None
        self.embedder_step = EmbedStep(process=embedder, context=self.context) if embedder else None
        self.stager_step = UploadStageStep(process=stager, context=self.context) if stager else None
        self.uploader_step = UploadStep(process=uploader, context=self.context)
        if self.context.uncompress:
            process = Uncompressor()
            self.uncompress_step = UncompressStep(process=process, context=self.context)

    def cleanup(self):
        pass

    def log_statuses(self):
        if status := self.context.status:
            logger.error(f"{len(status)} failed documents:")
            for k, v in status.items():
                for kk, vv in v.items():
                    logger.error(f"{k}: [{kk}] {vv}")

    def run(self):
        try:
            self._run()
        finally:
            self.log_statuses()
            self.cleanup()

    def clean_results(self, results: Optional[list[Union[Any, list[Any]]]]) -> Optional[list[Any]]:
        if not results:
            return None
        results = [r for r in results if r]
        flat = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
            else:
                flat.append(r)
        final = [f for f in flat if f]
        return final or None

    def _run(self):
        logger.info(f"Running local pipline: {self}")
        manager = mp.Manager()
        self.context.status = manager.dict()

        # Index into data source
        indices = self.indexer_step.run()
        indices_inputs = [{"file_data_path": i} for i in indices]
        if not indices_inputs:
            return

        # Download associated content to local file system
        downloaded_data = self.downloader_step(indices_inputs)
        downloaded_data = self.clean_results(results=downloaded_data)
        if not downloaded_data:
            return

        # Run uncompress if available
        if self.uncompress_step:
            downloaded_data = self.uncompress_step(downloaded_data)
            # Flatten list of lists
            downloaded_data = self.clean_results(results=downloaded_data)

        if not downloaded_data:
            return

        # Partition content
        elements = self.partitioner_step(downloaded_data)
        elements = self.clean_results(results=elements)
        if not elements:
            return

        # Run element specific modifiers
        for step in [self.chunker_step, self.embedder_step, self.stager_step]:
            elements = step(elements) if step else elements
            elements = self.clean_results(results=elements)
            if not elements:
                return

        # Upload the final result
        self.uploader_step(iterable=elements)

    def __str__(self):
        s = [str(self.indexer_step), str(self.downloader_step)]
        if uncompress_step := self.uncompress_step:
            s.append(str(uncompress_step))
        s.append(str(self.partitioner_step))
        if chunker_step := self.chunker_step:
            s.append(str(chunker_step))
        if embedder_step := self.embedder_step:
            s.append(str(embedder_step))
        if stager_step := self.stager_step:
            s.append(str(stager_step))
        s.append(str(self.uploader_step))
        return " -> ".join(s)
