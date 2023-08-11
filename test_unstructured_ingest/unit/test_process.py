import pytest

from unstructured.ingest.doc_processor.generalized import session_handle_var
from unstructured.ingest.processor import Processor


@pytest.fixture(autouse=True)
def _reset_session_handle():
    session_handle_var.set(None)

@pytest.mark.parametrize("test_verbose", [True, False])
def test_processor_init_with_session_handle(mocker, test_verbose):
    """Test that the init function calls to ingest_log_streaming_init and assigns the session handle
    when the a function is passed in."""
    mock_ingest_log_streaming_init = mocker.patch(
        "unstructured.ingest.processor.ingest_log_streaming_init",
    )
    mock_create_session_handle_fn = mocker.MagicMock()
    Processor.process_init(test_verbose, mock_create_session_handle_fn)
    mock_ingest_log_streaming_init.assert_called_once_with(test_verbose)
    mock_create_session_handle_fn.assert_called_once_with()
    assert (
        session_handle_var.get() == mock_create_session_handle_fn.return_value
    )

def test_processor_init_no_session_handle(mocker):
    """Test that the init function calls to ingest_log_streaming_init and does not assign the session handle
    when the a function is not passed in."""
    mock_ingest_log_streaming_init = mocker.patch(
        "unstructured.ingest.processor.ingest_log_streaming_init",
    )
    Processor.process_init(True)
    mock_ingest_log_streaming_init.assert_called_once_with(True)
    assert session_handle_var.get() is None
