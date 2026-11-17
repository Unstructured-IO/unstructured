import numpy as np
from unstructured_inference.inference.elements import TextRegions

from unstructured.partition.pdf_image.inference_utils import build_layout_elements_from_ocr_regions


def test_text_grouping_preserves_indices_after_consuming_repeated_words():
    texts = np.array(["noise", "a", "a", "b", "a", "b", "c", "c"])
    coords = np.array([[10 * index, 0, 10 * index + 8, 12] for index in range(len(texts))])
    regions = TextRegions(
        element_coords=coords.copy(), texts=texts.copy(), sources=np.array([None] * len(texts))
    )

    result = build_layout_elements_from_ocr_regions(
        regions, "a a b\n\na b\n\n\n\nc c", group_by_ocr_text=True
    )

    assert result.texts.tolist() == ["a a b", "a b", "c c"]
    np.testing.assert_array_equal(
        result.element_coords, [[10, 0, 38, 12], [40, 0, 58, 12], [60, 0, 78, 12]]
    )
    np.testing.assert_array_equal(regions.element_coords, coords)
    np.testing.assert_array_equal(regions.texts, texts)


def test_text_grouping_keeps_dense_page_paragraphs_and_bounds():
    paragraph_count = 30
    words_per_paragraph = 100
    paragraphs = [
        [f"p{paragraph}w{word}" for word in range(words_per_paragraph)]
        for paragraph in range(paragraph_count)
    ]
    texts = [word for paragraph in paragraphs for word in paragraph]
    coords = [
        [word * 10, paragraph * 20, word * 10 + 8, paragraph * 20 + 12]
        for paragraph in range(paragraph_count)
        for word in range(words_per_paragraph)
    ]
    regions = TextRegions(
        element_coords=np.array(coords),
        texts=np.array(texts),
        sources=np.array([None] * len(texts)),
    )
    expected_text = [" ".join(paragraph) for paragraph in paragraphs]

    result = build_layout_elements_from_ocr_regions(
        regions, "\n\n".join(expected_text), group_by_ocr_text=True
    )

    assert result.texts.tolist() == expected_text
    np.testing.assert_array_equal(
        result.element_coords,
        [[0, paragraph * 20, 998, paragraph * 20 + 12] for paragraph in range(paragraph_count)],
    )
