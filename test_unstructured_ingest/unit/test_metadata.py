from unstructured.ingest.connector.local import LocalIngestDoc, SimpleLocalConfig
from unstructured.ingest.interfaces import ProcessorConfig, ReadConfig


def test_local_metadata():
    doc = LocalIngestDoc(
        path="test_unstructured_ingest/example-docs/layout-parser-paper.pdf",
        connector_config=SimpleLocalConfig(input_path="test_unstructured_ingest/example-docs/"),
        processor_config=ProcessorConfig(),
        read_config=ReadConfig(),
    )

    source_meta = doc.source_metadata

    serialized_json = doc.to_json()

    deserialized_doc = LocalIngestDoc.from_json(serialized_json)

    assert source_meta == deserialized_doc.source_metadata
