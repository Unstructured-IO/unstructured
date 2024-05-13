import multiprocessing as mp
from dataclasses import InitVar, dataclass, field

from unstructured.ingest.v2.pipeline.context import PipelineContext
from unstructured.ingest.v2.pipeline.steps.chunk import Chunker, ChunkStep
from unstructured.ingest.v2.pipeline.steps.download import DownloadStep, download_type
from unstructured.ingest.v2.pipeline.steps.embed import Embedder, EmbedStep
from unstructured.ingest.v2.pipeline.steps.index import IndexStep, index_type
from unstructured.ingest.v2.pipeline.steps.partition import Partitioner, PartitionStep
from unstructured.ingest.v2.pipeline.steps.stage import UploadStager, UploadStageStep
from unstructured.ingest.v2.pipeline.steps.upload import Uploader, UploadStep


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
    embedder: InitVar[Embedder] = None
    embedder_step: EmbedStep = field(init=False, default=None)
    stager: InitVar[UploadStager] = None
    stager_step: UploadStageStep = field(init=False, default=None)
    uploader: InitVar[Uploader] = None
    uploader_step: UploadStep = field(init=False, default=None)

    def __post_init__(
        self,
        indexer: index_type,
        downloader: download_type,
        partitioner: Partitioner,
        chunker: Chunker = None,
        embedder: Embedder = None,
        stager: UploadStager = None,
        uploader: Uploader = None,
    ):
        self.indexer_step = IndexStep(process=indexer, context=self.context)
        self.downloader_step = DownloadStep(process=downloader, context=self.context)
        self.partitioner_step = PartitionStep(process=partitioner, context=self.context)
        self.chunker_step = ChunkStep(process=chunker, context=self.context) if chunker else None
        self.embedder_step = EmbedStep(process=embedder, context=self.context) if embedder else None
        self.stager_step = UploadStageStep(process=stager, context=self.context) if stager else None
        self.uploader_step = UploadStep(process=uploader, context=self.context)

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
        if self.embedder_step:
            elements = self.embedder_step(elements)
        if self.stager_step:
            elements = self.stager_step(elements)

        self.uploader_step.run(contents=elements)
