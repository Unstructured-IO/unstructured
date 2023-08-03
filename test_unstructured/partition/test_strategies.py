import os

import pytest

from unstructured.partition import pdf, strategies


def test_validate_strategy_validates():
    # Nothing should raise for a valid strategy
    strategies.validate_strategy("hi_res", "pdf")


def test_validate_strategy_raises_for_bad_filetype():
    with pytest.raises(ValueError):
        strategies.validate_strategy("fast", "image")


def test_validate_strategy_raises_for_bad_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy("totally_guess_the_text", "image")


@pytest.mark.parametrize(
    ("filename", "from_file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", True, True),
        ("copy-protected.pdf", True, True),
        ("loremipsum-flat.pdf", True, False),
        ("layout-parser-paper-fast.pdf", False, True),
        ("copy-protected.pdf", False, True),
        ("loremipsum-flat.pdf", False, False),
    ],
)
def test_is_pdf_text_extractable(filename, from_file, expected):
    filename = os.path.join("example-docs", filename)

    if from_file:
        with open(filename, "rb") as f:
            extractable = pdf.extractable_elements(file=f)
    else:
        extractable = pdf.extractable_elements(filename=filename)

    assert bool(extractable) is expected


def test_determine_image_auto_strategy():
    strategy = strategies._determine_image_auto_strategy()
    assert strategy == "hi_res"


@pytest.mark.parametrize(
    ("pdf_text_extractable", "infer_table_structure", "expected"),
    [
        (True, True, "hi_res"),
        (False, True, "hi_res"),
        (True, False, "fast"),
        (False, False, "ocr_only"),
    ],
)
def test_determine_image_pdf_strategy(pdf_text_extractable, infer_table_structure, expected):
    strategy = strategies._determine_pdf_auto_strategy(
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
    )
    assert strategy is expected


def test_determine_pdf_or_image_strategy_fallback_hi_res():
    strategy = strategies.determine_pdf_or_image_strategy(
        strategy="fast",
        is_image=True,
    )
    assert strategy == "hi_res"
