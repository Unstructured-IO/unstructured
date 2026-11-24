import pytest

from test_unstructured.unit_utils import FixtureRequest, Mock, method_mock
from unstructured.chunking.base import TokenCounter


@pytest.fixture()
def word_token_counter_(request: FixtureRequest) -> Mock:
    """Count one token per whitespace-delimited word.

    Deterministic and offline, so a test can state exact token counts without depending on
    tiktoken being installed or on the contents of a particular encoding.
    """
    return method_mock(
        request,
        TokenCounter,
        "count",
        side_effect=lambda _, text: len(text.split()),
    )
