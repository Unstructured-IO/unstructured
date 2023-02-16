"""Process aribritrary files with the Unstructured library"""

import logging

from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_isd

from unstructured_inference.models.detectron2 import MODEL_TYPES


def initialize():
    """Download models (avoids subprocesses all doing the same)"""
    ***REMOVED*** Accessing this dictionary triggers standard model downloads for pdf processing.
    ***REMOVED*** There will be a better way to do this, see
    ***REMOVED*** https://github.com/Unstructured-IO/unstructured-inference/issues/55
    MODEL_TYPES[None]["model_path"]
    MODEL_TYPES[None]["config_path"]


def process_document(doc):
    """Process any IngestDoc-like class of document with Unstructured's auto partition logic."""
    isd_elems_no_filename = None
    try:
        ***REMOVED*** does the work necessary to load file into filesystem
        ***REMOVED*** in the future, get_file_handle() could also be supported
        doc.get_file()

        ***REMOVED*** accessing the .filename property could lazily call .get_file(), but
        ***REMOVED*** keeping them as two distinct calls for end-user transparency for now
        print(f"Processing {doc.filename}")
        isd_elems = convert_to_isd(partition(filename=doc.filename))

        isd_elems_no_filename = []
        for elem in isd_elems:
            ***REMOVED*** type: ignore
            elem["metadata"].pop("filename")  ***REMOVED*** type: ignore[attr-defined]
            isd_elems_no_filename.append(elem)

        ***REMOVED*** Note, this may be a no-op if the IngestDoc doesn't do anything to persist
        ***REMOVED*** the results. Instead, the MainProcess (caller) may work with the aggregate
        ***REMOVED*** results across all docs in memory.
        doc.write_result(isd_elems_no_filename)

    except Exception:
        ***REMOVED*** TODO(crag) save the exception instead of print?
        logging.error(f"Failed to process {doc}", exc_info=True)
    else:
        doc.cleanup_file()
    finally:
        return isd_elems_no_filename
