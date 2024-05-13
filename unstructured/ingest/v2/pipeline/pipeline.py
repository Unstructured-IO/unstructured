import multiprocessing as mp
from dataclasses import InitVar, dataclass, field

from unstructured.ingest.v2.pipeline.context import PipelineContext
from unstructured.ingest.v2.pipeline.steps.chunk import Chunker, ChunkStep
from unstructured.ingest.v2.pipeline.steps.download import DownloadStep, download_type
from unstructured.ingest.v2.pipeline.steps.index import IndexStep, index_type
from unstructured.ingest.v2.pipeline.steps.partition import Partitioner, PartitionStep


@dataclass
class Pipeline:
    context: PipelineContext
    indexer: InitVar[index_type]
    indexer_step: IndexStep = field(init=False)
    downloader: InitVar[download_type]
    downloader_step: DownloadStep = field(init=False)
    partitioner: InitVar[Partitioner]
    partitioner_step: PartitionStep = field(init=False)
    chunker: InitVar[Chunker] = None
    chunker_step: ChunkStep = field(init=False, default=None)

    def __post_init__(
        self,
        indexer: index_type,
        downloader: download_type,
        partitioner: Partitioner,
        chunker: Chunker = None,
    ):
        self.indexer_step = IndexStep(process=indexer, context=self.context)
        self.downloader_step = DownloadStep(process=downloader, context=self.context)
        self.partitioner_step = PartitionStep(process=partitioner, context=self.context)
        self.chunker_step = ChunkStep(process=chunker, context=self.context) if chunker else None

    def run(self):
        manager = mp.Manager()
        self.context.statuses = manager.dict()
        indices = self.indexer_step.run()
        indies_inputs = [{"file_data_path": i} for i in indices]
        downloaded_data = self.downloader_step(indies_inputs)
        # Flatten list of lists
        downloaded_data_flat = [x for xs in downloaded_data for x in xs]
        elements = self.partitioner_step(downloaded_data_flat)
        if self.chunker_step:
            elements = self.chunker_step(elements)
