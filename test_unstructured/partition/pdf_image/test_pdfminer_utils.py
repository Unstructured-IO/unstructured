from unittest.mock import MagicMock

from pdfminer.layout import LTContainer, LTTextLine

from unstructured.partition.pdf_image.pdfminer_utils import extract_text_objects


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
