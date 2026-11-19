import csv
import io
import json
from copy import deepcopy

from unstructured.documents.elements import NarrativeText, Title
from unstructured.staging.prodigy import stage_csv_for_prodigy, stage_for_prodigy


def test_json_staging_can_reuse_metadata_without_changing_it():
    elements = [Title("Document"), NarrativeText("A paragraph.")]
    metadata = [{"source": "document"}, {"category": "paragraph"}]
    original = deepcopy(metadata)

    first = stage_for_prodigy(elements, metadata)
    second = stage_for_prodigy(elements, metadata)

    assert metadata == original
    assert second == first
    assert [row["meta"]["id"] for row in first] == [element.id for element in elements]


def test_shared_metadata_keeps_each_element_id_in_serialized_output():
    elements = [Title("First document"), Title("Second document")]
    shared_metadata = {"source": "same collection"}

    staged = stage_for_prodigy(elements, [shared_metadata, shared_metadata])
    serialized = json.loads(json.dumps(staged))

    assert serialized == [
        {"text": element.text, "meta": {"source": "same collection", "id": element.id}}
        for element in elements
    ]
    assert shared_metadata == {"source": "same collection"}


def test_output_metadata_is_independent_of_source_and_other_records():
    elements = [Title("First"), Title("Second")]
    shared_metadata = {"source": "original"}
    staged = stage_for_prodigy(elements, [shared_metadata, shared_metadata])

    staged[0]["meta"]["source"] = "edited output"
    shared_metadata["source"] = "edited input"

    assert staged[0]["meta"]["source"] == "edited output"
    assert staged[1]["meta"]["source"] == "original"
    assert staged[0]["meta"]["id"] == elements[0].id
    assert staged[1]["meta"]["id"] == elements[1].id


def test_json_then_csv_staging_can_share_metadata():
    elements = [Title("Document"), NarrativeText("A paragraph.")]
    metadata = [{"source": "first"}, {"source": "second"}]
    original = deepcopy(metadata)

    stage_for_prodigy(elements, metadata)
    rows = list(csv.DictReader(io.StringIO(stage_csv_for_prodigy(elements, metadata))))

    assert rows == [
        {"text": element.text, "id": element.id, "source": metadatum["source"]}
        for element, metadatum in zip(elements, original)
    ]
    assert metadata == original
