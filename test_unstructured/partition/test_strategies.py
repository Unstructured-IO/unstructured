import os

import pytest

from unstructured.partition import pdf, strategies
from unstructured.partition.utils.constants import PartitionStrategy


@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.AUTO,
        PartitionStrategy.FAST,
        PartitionStrategy.OCR_ONLY,
        PartitionStrategy.HI_RES,
    ],
)
def test_validate_strategy(strategy):
    # Nothing should raise for a valid strategy
    strategies.validate_strategy(strategy=strategy)


def test_validate_strategy_raises_for_fast_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy(strategy=PartitionStrategy.FAST, is_image=True)


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
        strategy=PartitionStrategy.FAST,
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
    )
    assert strategy == PartitionStrategy.FAST


@pytest.mark.parametrize(
    (
        "pdf_text_extractable",
        "infer_table_structure",
        "extract_images_in_pdf",
        "extract_element_types",
        "expected",
    ),
    [
        (True, True, True, ["Image"], PartitionStrategy.HI_RES),
        (True, True, True, [], PartitionStrategy.HI_RES),
        (True, True, False, ["Image"], PartitionStrategy.HI_RES),
        (True, True, False, [], PartitionStrategy.HI_RES),
        (True, False, True, ["Image"], PartitionStrategy.HI_RES),
        (True, False, True, [], PartitionStrategy.HI_RES),
        (True, False, False, ["Image"], PartitionStrategy.HI_RES),
        (True, False, False, [], PartitionStrategy.FAST),
        (False, True, True, ["Image"], PartitionStrategy.HI_RES),
        (False, True, True, [], PartitionStrategy.HI_RES),
        (False, True, False, ["Image"], PartitionStrategy.HI_RES),
        (False, True, False, [], PartitionStrategy.HI_RES),
        (False, False, True, ["Image"], PartitionStrategy.HI_RES),
        (False, False, True, [], PartitionStrategy.HI_RES),
        (False, False, False, ["Image"], PartitionStrategy.HI_RES),
        (False, False, False, [], PartitionStrategy.OCR_ONLY),
    ],
)
def test_determine_pdf_auto_strategy(
    pdf_text_extractable,
    infer_table_structure,
    extract_images_in_pdf,
    extract_element_types,
    expected,
):
    strategy = strategies.determine_pdf_or_image_strategy(
        strategy=PartitionStrategy.AUTO,
        is_image=False,
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
        extract_images_in_pdf=extract_images_in_pdf,
        extract_element_types=extract_element_types,
    )
    assert strategy == expected


def test_determine_image_auto_strategy():
    strategy = strategies.determine_pdf_or_image_strategy(
        strategy=PartitionStrategy.AUTO,
        is_image=True,
    )
    assert strategy == PartitionStrategy.HI_RES
