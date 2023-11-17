import pytest

from unstructured.partition import pdf
from unstructured.partition.utils.constants import PartitionStrategy


@pytest.fixture(scope="session")
def chipper_results():
    elements = pdf.partition_pdf(
        "example-docs/layout-parser-paper-fast.pdf",
        strategy=PartitionStrategy.HI_RES,
        model_name="chipper",
    )
    return elements


@pytest.fixture(scope="session")
def chipper_children(chipper_results):
    return [el for el in chipper_results if el.metadata.parent_id is not None]


@pytest.mark.chipper()
def test_chipper_has_hierarchy(chipper_children):
    assert chipper_children


@pytest.mark.chipper()
def test_chipper_not_losing_parents(chipper_results, chipper_children):
    assert all(
        [el for el in chipper_results if el.id == child.metadata.parent_id]
        for child in chipper_children
    )
