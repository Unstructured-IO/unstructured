from importlib import reload
from unittest.mock import MagicMock

from pdfminer.layout import LTChar, LTContainer, LTTextLine

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pdf_image.pdfminer_utils import (
    _is_duplicate_char,
    deduplicate_chars_in_text_line,
    extract_text_objects,
    get_text_with_deduplication,
)
from unstructured.partition.utils import config as partition_config


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


def _create_mock_ltchar(
    text: str, x0: float, y0: float, width: float = 6.0, height: float = 2.0
) -> MagicMock:
    """Helper to create a mock LTChar with specified text and position.

    Includes x1, y1 so _is_duplicate_char overlap logic works (fake-bold detection
    uses bounding box overlap). Default width/height give overlap ratio > 0.5 for
    chars within threshold distance.
    """
    mock_char = MagicMock(spec=LTChar)
    mock_char.get_text.return_value = text
    mock_char.x0 = x0
    mock_char.y0 = y0
    mock_char.x1 = x0 + width
    mock_char.y1 = y0 + height
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


# -- Integration tests for fake-bold PDF deduplication --


class TestFakeBoldPdfIntegration:
    """Integration tests for fake-bold PDF deduplication using real PDF files.

    The test PDF (fake-bold-sample.pdf) contains text rendered with the "fake bold"
    technique where each character is drawn twice at slightly offset positions.
    This causes text extraction to show doubled characters (e.g., "BBOOLLDD" instead
    of "BOLD") unless deduplication is applied.
    """

    def test_fake_bold_pdf_without_deduplication_shows_doubled_chars(self, monkeypatch):
        """Test that extraction WITHOUT deduplication shows doubled characters.

        When PDF_CHAR_DUPLICATE_THRESHOLD is set to 0, deduplication is disabled
        and the raw text shows the fake-bold doubled characters.
        """
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "0")
        reload(partition_config)

        filename = example_doc_path("pdf/fake-bold-sample.pdf")
        elements = partition_pdf(filename=filename, strategy="fast")
        extracted_text = " ".join([el.text for el in elements])

        # Without deduplication, fake-bold text appears with doubled characters
        assert "BBOOLLDD" in extracted_text, (
            "Without deduplication, fake-bold text should show doubled characters "
            "like 'BBOOLLDD' instead of 'BOLD'"
        )

    def test_fake_bold_pdf_with_deduplication_shows_clean_text(self, monkeypatch):
        """Test that extraction WITH deduplication shows clean text.

        When PDF_CHAR_DUPLICATE_THRESHOLD is set to default (2.0), deduplication
        removes the duplicate characters and produces clean, readable text.
        """
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "2.0")
        reload(partition_config)

        filename = example_doc_path("pdf/fake-bold-sample.pdf")
        elements = partition_pdf(filename=filename, strategy="fast")
        extracted_text = " ".join([el.text for el in elements])

        # With deduplication, fake-bold text should be clean (no doubled chars)
        assert "BOLD" in extracted_text, (
            "With deduplication, text should contain clean 'BOLD' not 'BBOOLLDD'"
        )
        # Verify the doubled pattern is NOT present in the deduplicated fake-bold section
        # Note: The PDF contains 'BBOOLLDD' as explanatory text, so we check for
        # the specific pattern that would appear if deduplication failed on the
        # fake-bold rendered text (e.g., "TTEEXXTT" from "TEXT")
        assert "TTEEXXTT" not in extracted_text, (
            "With deduplication, fake-bold 'TEXT' should not appear as 'TTEEXXTT'"
        )

    def test_fake_bold_deduplication_reduces_text_length(self, monkeypatch):
        """Test that deduplication reduces text length for fake-bold PDFs.

        Compares extraction with and without deduplication to verify that
        the deduplicated text is shorter due to removal of duplicate characters.
        """
        filename = example_doc_path("pdf/fake-bold-sample.pdf")

        # Extract WITHOUT deduplication (threshold=0)
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "0")
        reload(partition_config)
        elements_no_dedup = partition_pdf(filename=filename, strategy="fast")
        text_no_dedup = " ".join([el.text for el in elements_no_dedup])

        # Extract WITH deduplication (threshold=2.0)
        monkeypatch.setenv("PDF_CHAR_DUPLICATE_THRESHOLD", "2.0")
        reload(partition_config)
        elements_with_dedup = partition_pdf(filename=filename, strategy="fast")
        text_with_dedup = " ".join([el.text for el in elements_with_dedup])

        # Deduplicated text should be shorter than non-deduplicated text
        assert len(text_with_dedup) < len(text_no_dedup), (
            f"Deduplicated text ({len(text_with_dedup)} chars) should be shorter "
            f"than non-deduplicated text ({len(text_no_dedup)} chars)"
        )
