"""Process arbitrary files with the Unstructured library"""

import os
from typing import Any, Dict, List, Optional

from unstructured_inference.models.base import get_model

from unstructured.ingest.interfaces import BaseIngestDoc
from unstructured.ingest.logger import logger


def initialize():
    """Download default model or model specified by UNSTRUCTURED_HI_RES_MODEL_NAME environment
    variable (avoids subprocesses all doing the same)"""

    # If more than one model will be supported and left up to user selection
    supported_model = os.environ.get("UNSTRUCTURED_HI_RES_SUPPORTED_MODEL", "")
    if supported_model:
        for model_name in supported_model.split(","):
            get_model(model_name=model_name)

    get_model(os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME"))


def process_document(
    doc: BaseIngestDoc,
    **partition_kwargs,
) -> Dict[str, Optional[List[Dict[str, Any]]]]:
    """Process any IngestDoc-like class of document with chosen Unstructured's partition logic.

    Parameters
    ----------
    doc
        BaseIngestDoc class instance referencing document to process
    partition_kwargs
        ultimately the parameters passed to partition()
    """
    isd_dict = {}
    try:
        parents = [doc]
        while len(parents) > 0:
            parent = parents.pop()
            logger.info(f"Processing doc: {parent}")
            # does the work necessary to load file into filesystem, may generate child docs
            # in the future, get_file_handle() could also be supported
            parent.get_file()
            isd_elems_no_filename = parent.process_file(**partition_kwargs)

            isd_dict[str(doc._output_filename)] = isd_elems_no_filename

            # Note, this may be a no-op if the IngestDoc doesn't do anything to persist
            # the results. Instead, the MainProcess (caller) may work with the aggregate
            # results across all docs in memory.
            parent.write_result()

            parents.extend(parent.get_children())
    except Exception:
        # TODO(crag) save the exception instead of print?
        logger.error(f"Failed to process {doc}", exc_info=True)
    finally:
        doc.cleanup_file()
        return isd_dict
