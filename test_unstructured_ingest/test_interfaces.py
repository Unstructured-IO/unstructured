import os
import pathlib

import pytest

from unstructured.ingest.connector.git import GitIngestDoc, SimpleGitConfig
from unstructured.ingest.interfaces import StandardConnectorConfig

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "example-docs")

test_files = [
    "layout-parser-paper-fast.jpg",
    "layout-parser-paper-fast.pdf",
]


@pytest.mark.parametrize("filename", test_files)
def test_process_file_metadata_include_filename(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
        ),
        path=filename,
        config=SimpleGitConfig(
            metadata_include="filename",
        ),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert set(elem["metadata"].keys()) == {"filename"}


@pytest.mark.parametrize("filename", test_files)
def test_process_file_metadata_include_filename_pagenum(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            metadata_include="filename,page_number",
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert set(elem["metadata"].keys()) == {"filename", "page_number"}


@pytest.mark.parametrize("filename", test_files)
def test_process_file_metadata_exclude_filename(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            metadata_exclude="filename",
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert "filename" not in elem["metadata"].keys()


@pytest.mark.parametrize("filename", test_files)
def test_process_file_metadata_exclude_filename_pagenum(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            metadata_exclude="filename,page_number",
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert "filename" not in elem["metadata"].keys()
        assert "page_number" not in elem["metadata"].keys()


@pytest.mark.parametrize("filename", test_files)
def test_process_file_fields_include_default(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert {"element_id", "text", "type", "metadata"} == set(elem.keys())


@pytest.mark.parametrize("filename", test_files)
def test_process_file_fields_include_elementid(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            fields_include="element_id",
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")

    for elem in isd_elems:
        assert {"element_id"} == set(elem.keys())


@pytest.mark.parametrize("filename", test_files)
def test_process_file_flatten_metadata_filename(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            metadata_include="filename",
            flatten_metadata=True,
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")
    for elem in isd_elems:
        assert {"element_id", "text", "type", "filename"} == set(elem.keys())


@pytest.mark.parametrize("filename", test_files)
def test_process_file_flatten_metadata_filename_pagenum(filename: str):
    ingest_doc = GitIngestDoc(
        standard_config=StandardConnectorConfig(
            download_dir=EXAMPLE_DOCS_DIRECTORY,
            output_dir="",
            metadata_include="filename,page_number",
            flatten_metadata=True,
        ),
        path=filename,
        config=SimpleGitConfig(),
    )
    isd_elems = ingest_doc.process_file(strategy="hi_res")
    for elem in isd_elems:
        assert {"element_id", "text", "type", "filename", "page_number"} == set(elem.keys())
