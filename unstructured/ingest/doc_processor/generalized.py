"""Process aribritrary files with the Unstructured library"""

from typing import Any, Dict, List, Optional

from unstructured_inference.models.base import get_model

from unstructured.ingest.interfaces import BaseIngestDoc as IngestDoc
from unstructured.ingest.logger import logger


def initialize():
    """Download default model (avoids subprocesses all doing the same)"""

    get_model()


def process_document(doc: "IngestDoc", **partition_kwargs) -> Optional[List[Dict[str, Any]]]:
    """Process any IngestDoc-like class of document with chosen Unstructured's partition logic.

    Parameters
    ----------
    partition_kwargs
        ultimately the parameters passed to partition()
    """
    isd_elems_no_filename = None
    try:
        # does the work necessary to load file into filesystem
        # in the future, get_file_handle() could also be supported
        doc.get_file()

        isd_elems_no_filename = doc.process_file(**partition_kwargs)

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
