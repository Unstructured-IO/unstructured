import os
import shutil
from pathlib import Path

from unstructured.ingest.connector.registry import create_ingest_doc_from_dict
from unstructured.ingest.logger import logger
from unstructured.ingest.pipeline.interfaces import CopyNode


class Copier(CopyNode):
    def run(self, json_path: str):
        filename = os.path.basename(json_path)
        doc_hash = os.path.splitext(filename)[0]
        ingest_doc_dict = self.pipeline_context.ingest_docs_map[doc_hash]
        ingest_doc = create_ingest_doc_from_dict(ingest_doc_dict)
        desired_output = ingest_doc._output_filename
        Path(desired_output).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Copying {json_path} -> {desired_output}")
        shutil.copy(json_path, desired_output)
