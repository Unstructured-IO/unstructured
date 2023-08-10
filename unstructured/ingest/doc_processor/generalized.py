"""Process arbitrary files with the Unstructured library"""

from contextvars import ContextVar
import os
from typing import Any, Dict, List, Optional, cast

from unstructured_inference.models.base import get_model

from unstructured.ingest.interfaces import BaseIngestDoc as IngestDoc, BaseSessionHandle
from unstructured.ingest.interfaces import IngestDocSessionHandleMixin
from unstructured.ingest.logger import logger

# This is a context variable that can be set by the pool process to be used by the
# doc processor to assign the session handle to the doc. This is necessary because
# the session handle is not picklable and cannot be passed as an argument to the
# doc processor.

session_handle_var: ContextVar[Optional[BaseSessionHandle]] = ContextVar('session_handle', default=None)

def initialize():
    """Download default model or model specified by UNSTRUCTURED_HI_RES_MODEL_NAME environment
    variable (avoids subprocesses all doing the same)"""

    # If more than one model will be supported and left up to user selection
    supported_model = os.environ.get("UNSTRUCTURED_HI_RES_SUPPORTED_MODEL", "")
    if supported_model:
        for model_name in supported_model.split(","):
            get_model(model_name=model_name)

    get_model(os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME"))


def process_document(doc: "IngestDoc", **partition_kwargs) -> Optional[List[Dict[str, Any]]]:
    """Process any IngestDoc-like class of document with chosen Unstructured's partition logic.

    Parameters
    ----------
    partition_kwargs
        ultimately the parameters passed to partition()
    """
    isd_elems_no_filename = None
    try:
        # assign the session handle for the data source on the doc
        session_handle = session_handle_var.get()
        if session_handle is not None and isinstance(doc, IngestDocSessionHandleMixin):
            cast(IngestDocSessionHandleMixin, doc).session_handle = session_handle
        # does the work necessary to load file into filesystem
        # in the future, get_file_handle() could also be supported
        doc.get_file()

        isd_elems_no_filename = doc.process_file(**partition_kwargs)

        # Note, this may be a no-op if the IngestDoc doesn't do anything to persist
        # the results. Instead, the Processor (caller) may work with the aggregate
        # results across all docs in memory.
        doc.write_result()
    except Exception:
        # TODO(crag) save the exception instead of print?
        logger.error(f"Failed to process {doc}", exc_info=True)
    finally:
        doc.cleanup_file()
        return isd_elems_no_filename
