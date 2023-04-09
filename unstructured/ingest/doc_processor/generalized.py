"""Process aribritrary files with the Unstructured library"""

from typing import Any, Dict, List, Optional

from unstructured_inference.models.detectron2 import MODEL_TYPES

from unstructured.ingest.interfaces import BaseIngestDoc as IngestDoc
from unstructured.ingest.logger import logger


def initialize():
    """Download models (avoids subprocesses all doing the same)"""
    # Accessing this dictionary triggers standard model downloads for pdf processing.
    # There will be a better way to do this, see
    # https://github.com/Unstructured-IO/unstructured-inference/issues/55
    MODEL_TYPES[None]["model_path"]
    MODEL_TYPES[None]["config_path"]


def process_document(doc: "IngestDoc") -> Optional[List[Dict[str, Any]]]:
    """Process any IngestDoc-like class of document with Unstructured's auto partition logic."""
    isd_elems_no_filename = None
    try:
        # does the work necessary to load file into filesystem
        # in the future, get_file_handle() could also be supported
        doc.get_file()

        isd_elems_no_filename = doc.process_file()

        # Note, this may be a no-op if the IngestDoc doesn't do anything to persist
        # the results. Instead, the MainProcess (caller) may work with the aggregate
        # results across all docs in memory.
        doc.write_result()
    except Exception:
        # TODO(crag) save the exception instead of print?
        logger.error(f"Failed to process {doc}", exc_info=True)
    finally:
        doc.cleanup_file()
        return isd_elems_no_filename
