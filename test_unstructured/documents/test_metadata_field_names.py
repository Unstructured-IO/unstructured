import copy
import gc
import weakref

import pytest

from unstructured.documents.elements import ElementMetadata


@pytest.mark.parametrize("copy_first", [False, True])
def test_subclass_without_annotations_inherits_known_metadata_fields(copy_first: bool):
    class InheritedMetadata(ElementMetadata):
        pass

    metadata = InheritedMetadata(filename="document.pdf")
    if copy_first:
        metadata = copy.deepcopy(metadata)

    assert metadata.page_number is None
    assert metadata.text_as_html is None
    assert dict(metadata.known_fields) == {"filename": "document.pdf"}
    assert metadata.to_dict() == {"filename": "document.pdf"}


def test_subclasses_with_distinct_annotations_keep_their_own_field_definitions():
    class FirstMetadata(ElementMetadata):
        first: str

    class SecondMetadata(ElementMetadata):
        second: str

    first = FirstMetadata()
    second = SecondMetadata()

    assert first.first is None
    assert second.second is None
    with pytest.raises(AttributeError):
        _ = first.second
    with pytest.raises(AttributeError):
        _ = second.first
    first.first = "one"
    second.second = "two"
    assert dict(first.known_fields) == {"first": "one"}
    assert dict(second.known_fields) == {"second": "two"}


def test_metadata_copies_keep_dynamic_fields_independent_after_known_field_access():
    metadata = ElementMetadata(filename="document.pdf", languages=["eng"])
    metadata.custom = {"tags": ["original"]}
    assert metadata.page_number is None

    cloned = copy.deepcopy(metadata)
    cloned.languages.append("fra")
    cloned.custom["tags"].append("copy")

    assert metadata.to_dict() == {
        "filename": "document.pdf",
        "languages": ["eng"],
        "custom": {"tags": ["original"]},
    }
    assert dict(metadata.known_fields) == {"filename": "document.pdf", "languages": ["eng"]}
    assert cloned.languages == ["eng", "fra"]
    assert cloned.custom == {"tags": ["original", "copy"]}


@pytest.mark.parametrize("replace_mapping", [False, True])
def test_new_metadata_instances_see_rebuilt_or_modified_class_schemas(replace_mapping: bool):
    class CustomMetadata(ElementMetadata):
        old_field: str

    assert CustomMetadata().old_field is None
    if replace_mapping:
        CustomMetadata.__annotations__ = {"new_field": str}
    else:
        del CustomMetadata.__annotations__["old_field"]
        CustomMetadata.__annotations__["new_field"] = str

    metadata = CustomMetadata()

    assert metadata.new_field is None
    with pytest.raises(AttributeError):
        _ = metadata.old_field


def test_instance_annotation_overrides_keep_their_field_lookup_behavior():
    metadata = ElementMetadata()
    metadata.__annotations__ = {"instance_field": str}

    assert metadata.instance_field is None
    with pytest.raises(AttributeError):
        _ = metadata.page_number


def test_metadata_and_temporary_subclasses_are_released_after_field_access():
    def references():
        class TemporaryMetadata(ElementMetadata):
            temporary_field: str

        metadata = TemporaryMetadata()
        assert metadata.temporary_field is None
        return weakref.ref(metadata), weakref.ref(TemporaryMetadata)

    instance_ref, class_ref = references()
    gc.collect()

    assert instance_ref() is None
    assert class_ref() is None
