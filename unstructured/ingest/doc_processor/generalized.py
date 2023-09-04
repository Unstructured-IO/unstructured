"""Process arbitrary files with the Unstructured library"""

import os
from typing import Any, Dict, List, Optional

from unstructured_inference.models.base import get_model

from unstructured.ingest.connector.registry import create_ingest_doc_from_json
from unstructured.ingest.interfaces import (
    BaseSessionHandle,
    IngestDocSessionHandleMixin,
)
from unstructured.ingest.logger import logger

# module-level variable to store session handle
session_handle: Optional[BaseSessionHandle] = None


def initialize():
    """Download default model or model specified by UNSTRUCTURED_HI_RES_MODEL_NAME environment
    variable (avoids subprocesses all doing the same)"""

    # If more than one model will be supported and left up to user selection
    supported_model = os.environ.get("UNSTRUCTURED_HI_RES_SUPPORTED_MODEL", "")
    if supported_model:
        for model_name in supported_model.split(","):
            get_model(model_name=model_name)

    get_model(os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME"))


def process_document(ingest_doc_json: str, **partition_kwargs) -> Optional[List[Dict[str, Any]]]:
    """Process the serialized json for any IngestDoc-like class of document with chosen
    Unstructured partition logic.

    Parameters
    ----------
    partition_kwargs
        ultimately the parameters passed to partition()
    """
    global session_handle
    isd_elems_no_filename = None
    doc = None
    try:
        doc = create_ingest_doc_from_json(ingest_doc_json)
        if isinstance(doc, IngestDocSessionHandleMixin):
            if session_handle is None:
                # create via doc.session_handle, which is a property that creates a
                # session handle if one is not already defined
                session_handle = doc.session_handle
            else:
                doc.session_handle = session_handle
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
        if doc:
            doc.cleanup_file()
        return isd_elems_no_filename
