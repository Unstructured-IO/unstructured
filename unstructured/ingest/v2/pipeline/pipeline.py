import multiprocessing as mp
from dataclasses import InitVar, dataclass, field

from unstructured.ingest.v2.pipeline.context import PipelineContext
from unstructured.ingest.v2.pipeline.steps.download import DownloadStep, download_type
from unstructured.ingest.v2.pipeline.steps.index import IndexStep, index_type


@dataclass
class Pipeline:
    context: PipelineContext
    indexer: InitVar[index_type]
    indexer_step: IndexStep = field(init=False)
    downloader: InitVar[download_type]
    downloader_step: DownloadStep = field(init=False)

    def __post_init__(self, indexer: index_type, downloader: download_type):
        self.indexer_step = IndexStep(process=indexer, context=self.context)
        self.downloader_step = DownloadStep(process=downloader, context=self.context)

    def run(self):
        manager = mp.Manager()
        self.context.statuses = manager.dict()
        indices = self.indexer_step()
        file_paths = [i.path for i in indices]
        print(file_paths)
        downloaded_data = self.downloader_step(file_paths)
        print(downloaded_data)
