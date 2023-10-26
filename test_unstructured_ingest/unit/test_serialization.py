from unstructured.ingest.connector.local import LocalIngestDoc, SimpleLocalConfig
from unstructured.ingest.connector.registry import (
    create_ingest_doc_from_dict,
    create_ingest_doc_from_json,
)
from unstructured.ingest.interfaces import ProcessorConfig, ReadConfig

doc = LocalIngestDoc(
    path="test_unstructured_ingest/example-docs/layout-parser-paper.pdf",
    connector_config=SimpleLocalConfig(input_path="test_unstructured_ingest/example-docs/"),
    processor_config=ProcessorConfig(),
    read_config=ReadConfig(),
)
doc.update_source_metadata()
serialized_json = doc.to_json()
serialized_dict = doc.to_dict()


def test_manual_deserialization():
    deserialized_doc = LocalIngestDoc.from_json(serialized_json)
    assert doc == deserialized_doc


def test_registry_from_json():
    deserialized_doc = create_ingest_doc_from_json(serialized_json)
    assert doc == deserialized_doc


def test_registry_from_dict():
    deserialized_doc = create_ingest_doc_from_dict(serialized_dict)
    assert doc == deserialized_doc


def test_source_metadata_serialization():
    doc = LocalIngestDoc(
        path="test_unstructured_ingest/example-docs/layout-parser-paper.pdf",
        connector_config=SimpleLocalConfig(input_path="test_unstructured_ingest/example-docs/"),
        processor_config=ProcessorConfig(),
        read_config=ReadConfig(),
    )
    serialized_json = doc.to_dict()
    assert not serialized_json["_source_metadata"]

    doc.update_source_metadata()
    serialized_json_w_meta = doc.to_dict()
    assert serialized_json_w_meta["_source_metadata"]
