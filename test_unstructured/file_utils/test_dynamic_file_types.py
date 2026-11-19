import multiprocessing
import pickle
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO

import pytest

from unstructured.file_utils.filetype import detect_filetype
from unstructured.file_utils.model import FileType, create_file_type, register_partitioner

CUSTOM_NAME = "CUSTOM_PROCESS_DOCUMENT"
CUSTOM_MIME = "application/x-custom-process-document"


def _register_worker_type():
    create_file_type(CUSTOM_NAME, canonical_mime_type=CUSTOM_MIME, extensions=[".custom-process"])


def _describe_worker_type(file_type):
    return file_type.name, file_type.mime_type, file_type is FileType.from_mime_type(CUSTOM_MIME)


@pytest.fixture(autouse=True)
def isolated_file_type_registry(monkeypatch):
    attributes = dict(FileType.__dict__)
    monkeypatch.setattr(FileType, "_member_names_", FileType._member_names_.copy())
    monkeypatch.setattr(FileType, "_member_map_", FileType._member_map_.copy())
    monkeypatch.setattr(FileType, "_value2member_map_", FileType._value2member_map_.copy())
    yield
    for name in FileType._member_map_:
        if name not in attributes and name in FileType.__dict__:
            type.__delattr__(FileType, name)
        elif name in attributes and FileType.__dict__.get(name) is not attributes[name]:
            type.__setattr__(FileType, name, attributes[name])


def test_registered_types_support_lookup_by_name_and_value():
    custom = create_file_type(CUSTOM_NAME, canonical_mime_type=CUSTOM_MIME)

    assert FileType[CUSTOM_NAME] is custom
    assert getattr(FileType, CUSTOM_NAME) is custom
    assert FileType(custom.value) is custom


def test_registered_types_participate_in_enum_iteration_in_registration_order():
    before = list(FileType)
    first = create_file_type("CUSTOM_FIRST", canonical_mime_type="application/x-first")
    second = create_file_type("CUSTOM_SECOND", canonical_mime_type="application/x-second")

    assert list(FileType) == [*before, first, second]
    assert len(FileType) == len(before) + 2
    assert list(reversed(FileType)) == list(reversed([*before, first, second]))


@pytest.mark.parametrize("protocol", [0, pickle.HIGHEST_PROTOCOL])
def test_registered_types_round_trip_through_pickle(protocol):
    custom = create_file_type(CUSTOM_NAME, canonical_mime_type=CUSTOM_MIME)

    restored = pickle.loads(pickle.dumps({"file_type": custom}, protocol=protocol))

    assert restored["file_type"] is custom


def test_registered_types_can_be_sent_to_a_process_that_registers_the_same_type():
    _register_worker_type()
    custom = FileType[CUSTOM_NAME]

    with ProcessPoolExecutor(
        max_workers=1,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_register_worker_type,
    ) as executor:
        result = executor.submit(_describe_worker_type, custom).result(timeout=30)

    assert result == (CUSTOM_NAME, CUSTOM_MIME, True)


def test_reregistering_a_custom_name_replaces_it_without_duplicate_iteration_entries():
    before = list(FileType)
    create_file_type(CUSTOM_NAME, canonical_mime_type="application/x-old-custom")
    replacement = create_file_type(CUSTOM_NAME, canonical_mime_type=CUSTOM_MIME)

    assert list(FileType) == [*before, replacement]
    assert FileType[CUSTOM_NAME] is replacement
    assert getattr(FileType, CUSTOM_NAME) is replacement
    assert FileType(replacement.value) is replacement
    assert pickle.loads(pickle.dumps(replacement)) is replacement
    assert FileType.from_mime_type("application/x-old-custom") is None


def test_registration_keeps_builtin_members_and_their_values_unchanged():
    before = list(FileType)
    create_file_type(CUSTOM_NAME, canonical_mime_type=CUSTOM_MIME)

    for builtin in before:
        assert FileType[builtin.name] is builtin
        assert FileType(builtin.value) is builtin
        assert pickle.loads(pickle.dumps(builtin)) is builtin


@pytest.mark.parametrize(
    "name",
    ["TXT", "txt", "from_mime_type", "_member_map_", "name", "value", "__members__", "__iter__"],
)
def test_conflicting_registrations_raise_without_changing_the_registry(name):
    members = dict(FileType.__members__)
    values = FileType._value2member_map_.copy()
    ordered_members = list(FileType)
    member_properties = [(member, member.name, member.value) for member in ordered_members]

    with pytest.raises(ValueError):
        create_file_type(name, canonical_mime_type=CUSTOM_MIME)

    assert dict(FileType.__members__) == members
    assert FileType._value2member_map_ == values
    assert list(FileType) == ordered_members
    assert FileType.TXT is members["TXT"]
    for member, original_name, original_value in member_properties:
        assert member.name == original_name
        assert member.value == original_value


def test_custom_type_detection_aliases_and_partitioner_registration_keep_working():
    custom = create_file_type(
        CUSTOM_NAME,
        canonical_mime_type=CUSTOM_MIME,
        alias_mime_types=["application/x-custom-alias"],
        extensions=[".custom-process"],
        importable_package_dependencies=["json"],
        extra_name="custom",
    )

    @register_partitioner(custom)
    def partition_custom():
        pass

    assert FileType.from_extension(".custom-process") is custom
    assert FileType.from_mime_type("application/x-custom-alias") is custom
    assert (
        detect_filetype(file=BytesIO(b"custom format content"), content_type=CUSTOM_MIME) is custom
    )
    assert custom.importable_package_dependencies == ("json",)
    assert custom.extra_name == "custom"
    assert custom.partitioner_function_name == "partition_custom"
    assert custom.is_partitionable
