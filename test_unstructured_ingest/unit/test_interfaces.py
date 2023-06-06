import os
import pathlib
from dataclasses import dataclass

import pytest

from unstructured.ingest.connector.local import LocalIngestDoc, SimpleLocalConfig
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    StandardConnectorConfig,
)
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "../..", "example-docs")
TEST_DOWNLOAD_DIR="/tmp"
TEST_OUTPUT_DIR="/tmp"
TEST_ID="test"
TEST_FILE_PATH=os.path.join(EXAMPLE_DOCS_DIRECTORY, "book-war-and-peace-1p.txt")

@dataclass
class TestConfig(BaseConnectorConfig):
    id: str
    path: str

TEST_CONFIG=TestConfig(id=TEST_ID, path=TEST_FILE_PATH)

@dataclass
class TestIngestDoc(BaseIngestDoc):
    config: TestConfig

    @property
    def filename(self):
        return "test"
    
    def cleanup_file(self):
        pass

    def get_file(self):
        pass

    def has_output(self):
        return True
    
    def write_result(self, result):
        pass

@pytest.fixture()
def partition_test_results():
    # Reusable partition test results, calculated only once
    return partition(filename=str(TEST_FILE_PATH))

@pytest.fixture()
def partition_file_test_results(partition_test_results):
    # Reusable partition_file test results, calculated only once
    return convert_to_dict(partition_test_results)

def test_process_file_fields_include_default(mocker, partition_test_results):
    """Validate when metadata_include and metadata_exclude are not set, all fields:
    ("element_id", "text", "type", "metadata") are included"""
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    test_ingest_doc = TestIngestDoc(
        config=TEST_CONFIG,
        standard_config=StandardConnectorConfig(
            download_dir=TEST_DOWNLOAD_DIR,
            output_dir=TEST_OUTPUT_DIR,
            metadata_include="filename,page_number",
        ),
    )
    isd_elems = test_ingest_doc.process_file()
    assert len(isd_elems)
    for elem in isd_elems:
        assert {"element_id", "text", "type", "metadata"} == set(elem.keys())


def test_process_file_metadata_includes_filename_and_page_number(mocker, partition_test_results):
    """Validate when metadata_include is set to "filename,page_number",
    only filename is included in metadata"""
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    test_ingest_doc = TestIngestDoc(
        config=TEST_CONFIG,
        standard_config=StandardConnectorConfig(
            download_dir=TEST_DOWNLOAD_DIR,
            output_dir=TEST_OUTPUT_DIR,
            metadata_include="filename,page_number",
        ),
    )
    isd_elems = test_ingest_doc.process_file()
    assert len(isd_elems)
    for elem in isd_elems:
        assert set(elem["metadata"].keys()) == {"filename", "page_number"}

def test_process_file_metadata_exclude_filename_pagenum(mocker, partition_test_results):
    """Validate when metadata_exclude is set to "filename,page_number",
    neither filename nor page_number are included in metadata"""
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    test_ingest_doc = TestIngestDoc(
        config=TEST_CONFIG,
        standard_config=StandardConnectorConfig(
            download_dir=TEST_DOWNLOAD_DIR,
            output_dir=TEST_OUTPUT_DIR,
            metadata_exclude="filename,page_number",
        ),
    )
    isd_elems = test_ingest_doc.process_file()
    assert len(isd_elems)
    for elem in isd_elems:
        assert "filename" not in elem["metadata"].keys()
        assert "page_number" not in elem["metadata"].keys()

def test_process_file_flatten_metadata(mocker, partition_test_results):
    mocker.patch(
        "unstructured.ingest.interfaces.partition",
        return_value=partition_test_results,
    )
    test_ingest_doc = TestIngestDoc(
        config=TEST_CONFIG,
        standard_config=StandardConnectorConfig(
            download_dir=TEST_DOWNLOAD_DIR,
            output_dir=TEST_OUTPUT_DIR,
            metadata_include="filename,page_number",
            flatten_metadata=True,
        ),
    )
    isd_elems = test_ingest_doc.process_file()
    for elem in isd_elems:
        assert {"element_id", "text", "type", "filename", "page_number"} == set(elem.keys())
