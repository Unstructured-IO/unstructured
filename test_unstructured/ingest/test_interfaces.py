from dataclasses import dataclass

import pytest

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    StandardConnectorConfig,
)


@dataclass
class TestConnectorConfig(BaseConnectorConfig):
    """Test subclass for connector-specific attributes."""

    new_param: str


TEST_DOWNLOAD_DIR = "test_download_dir"
TEST_OUTPUT_DIR = "test_output_dir"
TEST_STANDARD_CONFIG = StandardConnectorConfig(
    download_dir=TEST_DOWNLOAD_DIR,
    output_dir=TEST_OUTPUT_DIR,
)


def test_base_connector_abstract():
    """Test that the BaseConnector class is abstract."""

    with pytest.raises(TypeError):
        BaseConnector()


def test_base_ingest_doc_abstract():
    """Test that the BaseIngestDoc class is abstract."""

    with pytest.raises(TypeError):
        BaseIngestDoc()


def test_ingest_doc_subclass():
    """Test a concrete subclass of BaseIngestDoc. It should be able to access the
    standard_config and config attributes of its parent classes."""

    @dataclass
    class TestIngestDoc(BaseIngestDoc):
        """A test subclass ingest doc"""

        new_param: str

        def filename(self):
            pass

        def cleanup_file(self):
            pass

        def get_file(self):
            pass

        def has_output(self):
            pass

        def write_result(self):
            pass

    test_connector_config_new_param = "test_connector_config_new_param"
    test_connector_config = TestConnectorConfig(new_param=test_connector_config_new_param)
    test_ingest_doc_new_param = "test_ingest_doc_new_param"
    test_ingest_doc = TestIngestDoc(
        TEST_STANDARD_CONFIG,
        test_connector_config,
        new_param=test_ingest_doc_new_param,
    )

    assert test_ingest_doc.standard_config.download_dir == TEST_DOWNLOAD_DIR
    assert test_ingest_doc.standard_config.output_dir == TEST_OUTPUT_DIR
    assert test_ingest_doc.config.new_param == test_connector_config_new_param
    assert test_ingest_doc.new_param == test_ingest_doc_new_param


def test_connector_subclass():
    """Test a concrete subclass of BaseConnector. It should be able to access the
    standard_config and config attributes of its parent classes."""

    class TestConnector(BaseConnector):
        """A test subclass connector"""

        def __init__(
            self,
            standard_config: StandardConnectorConfig,
            config: TestConnectorConfig,
        ):
            super().__init__(standard_config, config)

        def cleanup(self, cur_dir=None):
            pass

        def initialize(self):
            pass

        def get_ingest_docs(self):
            pass

    test_connector_config_new_param = "test_connector_config_new_param"

    test_connector_config = TestConnectorConfig(new_param=test_connector_config_new_param)
    test_connector = TestConnector(TEST_STANDARD_CONFIG, test_connector_config)

    assert test_connector.standard_config.download_dir == TEST_DOWNLOAD_DIR
    assert test_connector.standard_config.output_dir == TEST_OUTPUT_DIR
    assert test_connector.config.new_param == test_connector_config_new_param
