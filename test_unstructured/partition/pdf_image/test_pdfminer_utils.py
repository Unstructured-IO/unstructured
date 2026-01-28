from unittest.mock import MagicMock

from pdfminer.layout import LTChar, LTContainer, LTTextLine

from unstructured.partition.pdf_image.pdfminer_utils import (
    _is_duplicate_char,
    deduplicate_chars_in_text_line,
    extract_text_objects,
    get_text_with_deduplication,
)


def test_extract_text_objects_nested_containers():
    """Test extract_text_objects with nested LTContainers."""
    # Mock LTTextLine objects
    mock_text_line1 = MagicMock(spec=LTTextLine)
    mock_text_line2 = MagicMock(spec=LTTextLine)

    # Mock inner container containing one LTTextLine
    mock_inner_container = MagicMock(spec=LTContainer)
    mock_inner_container.__iter__.return_value = [mock_text_line2]

    # Mock outer container containing another LTTextLine and the inner container
    mock_outer_container = MagicMock(spec=LTContainer)
    mock_outer_container.__iter__.return_value = [mock_text_line1, mock_inner_container]

    # Call the function with the outer container
    result = extract_text_objects(mock_outer_container)

    # Assert both text line objects are extracted, even from nested containers
    assert len(result) == 2
    assert mock_text_line1 in result
    assert mock_text_line2 in result


# -- Tests for character deduplication (fake bold fix) --


def _create_mock_ltchar(text: str, x0: float, y0: float) -> MagicMock:
    """Helper to create a mock LTChar with specified text and position."""
    mock_char = MagicMock(spec=LTChar)
    mock_char.get_text.return_value = text
    mock_char.x0 = x0
    mock_char.y0 = y0
    return mock_char


class TestIsDuplicateChar:
    """Tests for _is_duplicate_char function."""

    def test_same_char_same_position_is_duplicate(self):
        """Two identical characters at the same position should be duplicates."""
        char1 = _create_mock_ltchar("A", 10.0, 20.0)
        char2 = _create_mock_ltchar("A", 10.0, 20.0)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is True

    def test_same_char_close_position_is_duplicate(self):
        """Two identical characters at close positions should be duplicates."""
        char1 = _create_mock_ltchar("B", 10.0, 20.0)
        char2 = _create_mock_ltchar("B", 11.5, 21.0)  # Within 3.0 threshold
        assert _is_duplicate_char(char1, char2, threshold=3.0) is True

    def test_same_char_far_position_not_duplicate(self):
        """Two identical characters at far positions should not be duplicates."""
        char1 = _create_mock_ltchar("C", 10.0, 20.0)
        char2 = _create_mock_ltchar("C", 15.0, 20.0)  # 5.0 > 3.0 threshold
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

    def test_different_chars_same_position_not_duplicate(self):
        """Two different characters at the same position should not be duplicates."""
        char1 = _create_mock_ltchar("A", 10.0, 20.0)
        char2 = _create_mock_ltchar("B", 10.0, 20.0)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

    def test_threshold_boundary(self):
        """Test behavior at exact threshold boundary."""
        char1 = _create_mock_ltchar("X", 10.0, 20.0)
        char2 = _create_mock_ltchar("X", 13.0, 20.0)  # Exactly at threshold
        # At threshold means NOT within threshold (uses < not <=)
        assert _is_duplicate_char(char1, char2, threshold=3.0) is False

        char3 = _create_mock_ltchar("X", 12.9, 20.0)  # Just under threshold
        assert _is_duplicate_char(char1, char3, threshold=3.0) is True


class TestDeduplicateCharsInTextLine:
    """Tests for deduplicate_chars_in_text_line function."""

    def test_no_duplicates_returns_original(self):
        """Text line without duplicates should return original text."""
        chars = [
            _create_mock_ltchar("H", 10.0, 20.0),
            _create_mock_ltchar("i", 15.0, 20.0),
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)
        mock_text_line.get_text.return_value = "Hi"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "Hi"

    def test_fake_bold_duplicates_removed(self):
        """Fake bold text (each char doubled) should be deduplicated."""
        # Simulates "BOLD" rendered as "BBOOLLDD" with duplicate positions
        chars = [
            _create_mock_ltchar("B", 10.0, 20.0),
            _create_mock_ltchar("B", 10.5, 20.0),  # Duplicate
            _create_mock_ltchar("O", 20.0, 20.0),
            _create_mock_ltchar("O", 20.5, 20.0),  # Duplicate
            _create_mock_ltchar("L", 30.0, 20.0),
            _create_mock_ltchar("L", 30.5, 20.0),  # Duplicate
            _create_mock_ltchar("D", 40.0, 20.0),
            _create_mock_ltchar("D", 40.5, 20.0),  # Duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "BOLD"

    def test_threshold_zero_disables_deduplication(self):
        """Setting threshold to 0 should disable deduplication."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.get_text.return_value = "BBOOLLDD"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=0)
        assert result == "BBOOLLDD"

    def test_negative_threshold_disables_deduplication(self):
        """Setting negative threshold should disable deduplication."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.get_text.return_value = "BBOOLLDD"

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=-1.0)
        assert result == "BBOOLLDD"

    def test_empty_text_line(self):
        """Empty text line should return original text."""
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter([])
        mock_text_line.get_text.return_value = ""

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == ""

    def test_legitimate_repeated_chars_preserved(self):
        """Legitimate repeated characters (different positions) should be preserved."""
        # "AA" where both A's are at different positions
        chars = [
            _create_mock_ltchar("A", 10.0, 20.0),
            _create_mock_ltchar("A", 20.0, 20.0),  # Different position, not duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = deduplicate_chars_in_text_line(mock_text_line, threshold=3.0)
        assert result == "AA"


class TestGetTextWithDeduplication:
    """Tests for get_text_with_deduplication function."""

    def test_with_text_line(self):
        """Should properly deduplicate text from LTTextLine."""
        chars = [
            _create_mock_ltchar("H", 10.0, 20.0),
            _create_mock_ltchar("H", 10.5, 20.0),  # Duplicate
            _create_mock_ltchar("i", 20.0, 20.0),
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        result = get_text_with_deduplication(mock_text_line, threshold=3.0)
        assert result == "Hi"

    def test_with_container(self):
        """Should handle LTContainer with nested LTTextLine."""
        chars = [
            _create_mock_ltchar("T", 10.0, 20.0),
            _create_mock_ltchar("T", 10.5, 20.0),  # Duplicate
        ]
        mock_text_line = MagicMock(spec=LTTextLine)
        mock_text_line.__iter__ = lambda self: iter(chars)

        mock_container = MagicMock(spec=LTContainer)
        mock_container.__iter__ = lambda self: iter([mock_text_line])

        result = get_text_with_deduplication(mock_container, threshold=3.0)
        assert result == "T"

    def test_with_generic_object(self):
        """Should fall back to get_text() for non-standard objects."""
        mock_obj = MagicMock()
        mock_obj.get_text.return_value = "fallback text"

        result = get_text_with_deduplication(mock_obj, threshold=3.0)
        assert result == "fallback text"

    def test_without_get_text(self):
        """Should return empty string for objects without get_text."""
        mock_obj = MagicMock(spec=[])  # No get_text method

        result = get_text_with_deduplication(mock_obj, threshold=3.0)
        assert result == ""
