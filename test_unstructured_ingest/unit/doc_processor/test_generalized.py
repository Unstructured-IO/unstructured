from dataclasses import dataclass

import pytest

from unstructured.ingest.interfaces import BaseIngestDoc, IngestDocSessionHandleMixin


@dataclass
class IngestDocWithSessionHandle(IngestDocSessionHandleMixin, BaseIngestDoc):
    pass

def test_process_document_with_session_handle(mocker):
    """Test that the process_document function calls the doc_processor_fn with the correct
    arguments, assigns the session handle, and returns the correct results."""
    mock_doc = mocker.MagicMock(spec=(IngestDocWithSessionHandle))
    mocker.patch("unstructured.ingest.connector.registry.create_ingest_doc_from_json", return_value=mock_doc)
    mock_session_handle = mocker.MagicMock()
    mocker.patch("unstructured.ingest.doc_processor.generalized.session_handle", mock_session_handle)

    # import here to account for the patching above
    from unstructured.ingest.doc_processor.generalized import process_document
    result = process_document(mocker.MagicMock())
    
    mock_doc.get_file.assert_called_once_with()
    mock_doc.write_result.assert_called_with()
    mock_doc.cleanup_file.assert_called_once_with()
    assert result == mock_doc.process_file.return_value 
    assert mock_doc.session_handle == mock_session_handle


def test_process_document_no_session_handle(mocker):
    """Test that the process_document function calls does not assign session handle the IngestDoc
    does not have the session handle mixin."""
    mock_doc = mocker.MagicMock(spec=(BaseIngestDoc))
    mocker.patch("unstructured.ingest.connector.registry.create_ingest_doc_from_json", return_value=mock_doc)
    mocker.patch("unstructured.ingest.doc_processor.generalized.session_handle", mocker.MagicMock())

    # import here to account for the patching above
    from unstructured.ingest.doc_processor.generalized import process_document
    process_document(mock_doc)

    assert not hasattr(mock_doc, "session_handle")
