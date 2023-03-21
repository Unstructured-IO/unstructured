import os
import pathlib

import pytest

from unstructured.ingest.connector.git import GitIngestDoc, SimpleGitConfig

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "example-docs")

test_files = [
    "layout-parser-paper-fast.jpg",
    "layout-parser-paper-fast.pdf",
]


@pytest.mark.parametrize("filename", test_files)
def test_process_file_include_filename(filename: str):
    ingest_doc = GitIngestDoc(
        path=filename,
        config=SimpleGitConfig(
          download_dir=EXAMPLE_DOCS_DIRECTORY,
          metadata_include="filename",
        ),
    )
    isd_elems = ingest_doc.process_file()

    for elem in isd_elems:
        for k in elem["metadata"]:
            assert k == "filename"


@pytest.mark.parametrize("filename", test_files)
def test_process_file_include_filename_pagenum(filename: str):
    ingest_doc = GitIngestDoc(
        path=filename,
        config=SimpleGitConfig(
          download_dir=EXAMPLE_DOCS_DIRECTORY,
          metadata_include="filename,page_number",
        ),
    )
    isd_elems = ingest_doc.process_file()

    for elem in isd_elems:
        for k in elem["metadata"]:
            assert k in ["filename", "page_number"]


@pytest.mark.parametrize("filename", test_files)
def test_process_file_exclude_filename(filename: str):
    ingest_doc = GitIngestDoc(
        path=filename,
        config=SimpleGitConfig(
          download_dir=EXAMPLE_DOCS_DIRECTORY,
          metadata_exclude="filename",
        ),
    )
    isd_elems = ingest_doc.process_file()

    for elem in isd_elems:
        for k in elem["metadata"]:
            assert k != "filename"


@pytest.mark.parametrize("filename", test_files)
def test_process_file_exclude_filename_pagenum(filename: str):
    ingest_doc = GitIngestDoc(
        path=filename,
        config=SimpleGitConfig(
          download_dir=EXAMPLE_DOCS_DIRECTORY,
          metadata_exclude="filename,page_number",
        ),
    )
    isd_elems = ingest_doc.process_file()

    for elem in isd_elems:
        for k in elem["metadata"]:
            assert k not in ["filename", "page_number"]
