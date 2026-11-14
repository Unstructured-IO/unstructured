"""COCO annotations must identify the image represented by each source element."""

import json
from copy import deepcopy

import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, Text
from unstructured.staging.base import convert_to_coco


def make_element(element_id: str, **changes) -> Text:
    """Build an annotated page with independently adjustable image identity fields."""
    metadata = {"filename": "document.pdf", "file_directory": "source", "page_number": 1}
    width = changes.pop("width", 100)
    height = changes.pop("height", 200)
    metadata.update(changes)
    return Text(
        "sample",
        element_id=element_id,
        metadata=ElementMetadata(**metadata),
        coordinates=((1, 2), (1, 8), (5, 8), (5, 2)),
        coordinate_system=PixelSpace(width, height),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"filename": "other.pdf"},
        {"file_directory": "other"},
        {"page_number": 2},
        {"width": 300},
        {"height": 400},
    ],
)
def test_annotations_follow_all_existing_image_identity_fields(change):
    elements = [make_element("a"), make_element("b", **change), make_element("c")]
    before = deepcopy([element.to_dict() for element in elements])

    exported = convert_to_coco(elements)

    assert [annotation["image_id"] for annotation in exported["annotations"]] == [1, 2, 1]
    assert [image["id"] for image in exported["images"]] == [1, 2]
    assert [annotation["id"] for annotation in exported["annotations"]] == ["a", "b", "c"]
    assert [element.to_dict() for element in elements] == before


@pytest.mark.parametrize("as_iterator", [False, True])
def test_image_ids_keep_first_seen_order_when_pages_recur(as_iterator):
    elements = [
        make_element(str(index), page_number=page) for index, page in enumerate([2, 1, 2, 3, 1])
    ]

    exported = convert_to_coco(iter(elements) if as_iterator else elements)

    assert [(image["id"], image["page_number"]) for image in exported["images"]] == [
        (1, 2),
        (2, 1),
        (3, 3),
    ]
    assert [annotation["image_id"] for annotation in exported["annotations"]] == [1, 2, 1, 3, 2]


def test_elements_without_image_metadata_share_the_existing_default_image():
    exported = convert_to_coco([Text("one", element_id="a"), Text("two", element_id="b")])

    assert len(exported["images"]) == 1
    assert [annotation["image_id"] for annotation in exported["annotations"]] == [1, 1]
    assert all(annotation["bbox"] == [] for annotation in exported["annotations"])


def test_empty_coco_export_has_no_images_or_annotations():
    exported = convert_to_coco(iter(()))

    assert exported["images"] == []
    assert exported["annotations"] == []


def test_export_can_be_indexed_and_filtered_by_the_native_coco_reader(tmp_path):
    coco_module = pytest.importorskip("pycocotools.coco")
    elements = [make_element("a"), make_element("b", page_number=2), make_element("c")]
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps(convert_to_coco(elements)), encoding="utf-8")

    dataset = coco_module.COCO(str(path))

    assert dataset.getAnnIds(imgIds=[1]) == ["a", "c"]
    assert dataset.getAnnIds(imgIds=[2]) == ["b"]
    assert dataset.loadImgs([1])[0]["page_number"] == 1
    assert dataset.loadImgs([2])[0]["page_number"] == 2
