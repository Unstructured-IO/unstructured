import pytest

from unstructured.ingest.error import (
    DestinationConnectionError,
    PartitionError,
    SourceConnectionError,
)


@pytest.mark.parametrize(
    ("error_class", "exception_type", "error_message"),
    [
        (SourceConnectionError, ValueError, "Simulated connection error"),
        (DestinationConnectionError, RuntimeError, "Simulated connection error"),
        (PartitionError, FileNotFoundError, "Simulated partition error"),
    ],
)
def test_custom_error_decorator(error_class, exception_type, error_message):
    @error_class.wrap
    def simulate_error():
        raise exception_type(error_message)

    with pytest.raises(error_class) as context:
        simulate_error()

    expected_error_string = error_class.error_string.format(error_message)
    assert str(context.value) == expected_error_string
