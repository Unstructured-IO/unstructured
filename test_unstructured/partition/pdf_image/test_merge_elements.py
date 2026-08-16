import numpy as np
from PIL import Image
from unstructured_inference.constants import IsExtracted
from unstructured_inference.inference.elements import Rectangle
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElement, LayoutElements

from unstructured.partition.pdf_image.pdfminer_processing import (
    array_merge_inferred_layout_with_extracted_layout,
    merge_inferred_with_extracted_layout,
)


def test_text_source_preserved_during_merge():
    """Test that text_source property is preserved when elements are merged."""

    # Create two simple LayoutElements with different text_source values
    inferred_element = LayoutElement(
        bbox=Rectangle(0, 0, 100, 50), text=None, is_extracted=IsExtracted.FALSE
    )

    extracted_element = LayoutElement(
        bbox=Rectangle(0, 0, 100, 50), text="Extracted text", is_extracted=IsExtracted.TRUE
    )

    # Create LayoutElements arrays
    inferred_layout_elements = LayoutElements.from_list([inferred_element])
    extracted_layout_elements = LayoutElements.from_list([extracted_element])

    # Create a PageLayout for the inferred layout
    image = Image.new("RGB", (200, 200))
    inferred_page = PageLayout(number=1, image=image)
    inferred_page.elements_array = inferred_layout_elements

    # Create DocumentLayout from the PageLayout
    inferred_document_layout = DocumentLayout(pages=[inferred_page])

    # Merge them
    merged_layout = merge_inferred_with_extracted_layout(
        inferred_document_layout=inferred_document_layout,
        extracted_layout=[extracted_layout_elements],
        hi_res_model_name="test_model",
    )

    # Verify text_source is preserved
    # Check the merged page's elements_array
    merged_page = merged_layout.pages[0]
    assert "Extracted text" in merged_page.elements_array.texts
    assert hasattr(merged_page.elements_array, "is_extracted_array")
    assert IsExtracted.TRUE in merged_page.elements_array.is_extracted_array


def test_single_extracted_region_at_index_zero_removes_inferred_subregion():
    """A lone extracted text region (at index 0) must still absorb an inferred subregion.

    Regression test: the subregion-removal rule was gated on ``any(extracted_to_keep)`` where
    ``extracted_to_keep`` holds element *indices*. When the only kept extracted region was at
    index 0, ``any([0])`` evaluated False and the rule was skipped, leaving the inferred box as
    a duplicate of the extracted region. This happens with single-region pages such as a PDF
    whose only text is a filled form field.
    """
    # Inferred (non-table) box fully contained by the single extracted text region.
    inferred = LayoutElements(
        element_coords=np.array([[10.0, 10.0, 40.0, 40.0]]),
        texts=np.array([None], dtype=object),
        element_class_ids=np.array([0]),
        element_class_id_map={0: "Section-header"},
    )
    extracted = LayoutElements(
        element_coords=np.array([[0.0, 0.0, 100.0, 50.0]]),
        texts=np.array(["Extracted text"], dtype=object),
        element_class_ids=np.array([0]),
        element_class_id_map={0: "UncategorizedText"},
    )

    merged = array_merge_inferred_layout_with_extracted_layout(
        inferred_layout=inferred,
        extracted_layout=extracted,
        page_image_size=(200, 200),
    )

    # The inferred subregion is removed; only the extracted region remains.
    assert len(merged) == 1
    assert list(merged.texts) == ["Extracted text"]
