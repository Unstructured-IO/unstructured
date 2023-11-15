import os

import pytest

from unstructured.partition import pdf, strategies


@pytest.mark.parametrize("strategy", ["auto", "fast", "ocr_only", "hi_res"])
def test_validate_strategy(strategy):
    # Nothing should raise for a valid strategy
    strategies.validate_strategy(strategy=strategy)


def test_validate_strategy_raises_for_fast_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy(strategy="fast", is_image=True)


def test_validate_strategy_raises_for_bad_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy("totally_guess_the_text")


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
def test_determine_pdf_auto_strategy(pdf_text_extractable, infer_table_structure, expected):
    strategy = strategies._determine_pdf_auto_strategy(
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
    )
    assert strategy is expected


@pytest.mark.parametrize(
    ("pdf_text_extractable", "infer_table_structure"),
    [
        (True, True),
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_determine_pdf_or_image_fast_strategy(pdf_text_extractable, infer_table_structure):
    strategy = strategies.determine_pdf_or_image_strategy(
        strategy="fast",
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
    )
    assert strategy == "fast"
