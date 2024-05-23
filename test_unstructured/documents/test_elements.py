# pyright: reportPrivateUsage=false

"""Test-suite for `unstructured.documents.elements` module."""

from __future__ import annotations

import copy
import io
import json
import pathlib
from functools import partial

import pytest

from test_unstructured.unit_utils import assign_hash_ids, example_doc_path
from unstructured.cleaners.core import clean_bullets, clean_prefix
from unstructured.documents.coordinates import (
    CoordinateSystem,
    Orientation,
    RelativeCoordinateSystem,
)
from unstructured.documents.elements import (
    CheckBox,
    ConsolidationStrategy,
    CoordinatesMetadata,
    DataSourceMetadata,
    Element,
    ElementMetadata,
    Points,
    RegexMetadata,
    Text,
    Title,
    assign_and_map_hash_ids,
)
from unstructured.partition.json import partition_json


@pytest.mark.parametrize("element", [Element(), Text(text=""), CheckBox()])
def test_Element_autoassigns_a_UUID_then_becomes_an_idempotent_and_deterministic_hash(
    element: Element,
):
    # -- element self-assigns itself a UUID --
    assert isinstance(element.id, str)
    assert len(element.id) == 36
    assert element.id.count("-") == 4

    expected_hash = "5336294a19f32ff03ef80066fbc3e0f7"
    # -- calling `.id_to_hash()` changes the element's id-type to hash --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash

    # -- `.id_to_hash()` is idempotent --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash


def test_Text_is_JSON_serializable():
    # -- This shold run without an error --
    json.dumps(Text(text="hello there!", element_id=None).to_dict())


@pytest.mark.parametrize(
    "element",
    [
        Element(),
        Text(text=""),  # -- element_id should be implicitly None --
        Text(text="", element_id=None),  # -- setting explicitly to None --
        CheckBox(),
    ],
)
def test_Element_self_assigns_itself_a_UUID_id(element: Element):
    assert isinstance(element.id, str)
    assert len(element.id) == 36
    assert element.id.count("-") == 4


def test_text_element_apply_cleaners():
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")

    text_element.apply(partial(clean_prefix, pattern=r"\[\d{1,2}\]"))
    assert str(text_element) == "A Textbook on Crocodile Habitats"


def test_text_element_apply_multiple_cleaners():
    cleaners = [partial(clean_prefix, pattern=r"\[\d{1,2}\]"), partial(clean_bullets)]
    text_element = Text(text="[1] \u2022 A Textbook on Crocodile Habitats")
    text_element.apply(*cleaners)
    assert str(text_element) == "A Textbook on Crocodile Habitats"


def test_non_text_elements_are_serializable_to_text():
    element = CheckBox()
    assert hasattr(element, "text")
    assert element.text is not None
    assert element.text == ""
    assert str(element) == ""


def test_apply_raises_if_func_does_not_produce_string():
    def bad_cleaner(s: str):
        return 1

    text_element = Text(text="[1] A Textbook on Crocodile Habitats")

    with pytest.raises(ValueError, match="Cleaner produced a non-string output."):
        text_element.apply(bad_cleaner)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("coordinates", "orientation1", "orientation2", "expected_coords"),
    [
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.CARTESIAN,
            Orientation.CARTESIAN,
            ((10, 20), (10, 40), (30, 40), (30, 20)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.CARTESIAN,
            Orientation.SCREEN,
            ((10, 1980), (10, 1960), (30, 1960), (30, 1980)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.SCREEN,
            Orientation.CARTESIAN,
            ((10, 1980), (10, 1960), (30, 1960), (30, 1980)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.SCREEN,
            Orientation.SCREEN,
            ((10, 20), (10, 40), (30, 40), (30, 20)),
        ),
    ],
)
def test_convert_coordinates_to_new_system(
    coordinates: Points,
    orientation1: Orientation,
    orientation2: Orientation,
    expected_coords: Points,
):
    coord1 = CoordinateSystem(100, 200)
    coord1.orientation = orientation1
    coord2 = CoordinateSystem(1000, 2000)
    coord2.orientation = orientation2
    element = Element(coordinates=coordinates, coordinate_system=coord1)

    new_coords = element.convert_coordinates_to_new_system(coord2)

    assert new_coords is not None
    for new_coord, expected in zip(new_coords, expected_coords):
        assert new_coord == pytest.approx(expected)  # pyright: ignore[reportUnknownMemberType]
    element.convert_coordinates_to_new_system(coord2, in_place=True)
    assert element.metadata.coordinates is not None
    assert element.metadata.coordinates.points is not None
    for new_coord, expected in zip(element.metadata.coordinates.points, expected_coords):
        assert new_coord == pytest.approx(expected)  # pyright: ignore[reportUnknownMemberType]
    assert element.metadata.coordinates.system == coord2


def test_convert_coordinate_to_new_system_none():
    element = Element(coordinates=None, coordinate_system=None)
    coord = CoordinateSystem(100, 200)
    coord.orientation = Orientation.SCREEN
    assert element.convert_coordinates_to_new_system(coord) is None


def test_element_constructor_coordinates_all_present():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    element = Element(coordinates=coordinates, coordinate_system=coordinate_system)
    expected_coordinates_metadata = CoordinatesMetadata(
        points=coordinates,
        system=coordinate_system,
    )
    assert element.metadata.coordinates == expected_coordinates_metadata


def test_element_constructor_coordinates_points_absent():
    with pytest.raises(ValueError) as exc_info:
        Element(coordinate_system=RelativeCoordinateSystem())
    assert (
        str(exc_info.value)
        == "Coordinates points should not exist without coordinates system and vice versa."
    )


def test_element_constructor_coordinates_system_absent():
    with pytest.raises(ValueError) as exc_info:
        Element(coordinates=((1, 2), (1, 4), (3, 4), (3, 2)))
    assert (
        str(exc_info.value)
        == "Coordinates points should not exist without coordinates system and vice versa."
    )


def test_coordinate_metadata_serdes():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    coordinates_metadata = CoordinatesMetadata(points=coordinates, system=coordinate_system)
    expected_schema = {
        "layout_height": 1,
        "layout_width": 1,
        "points": ((1, 2), (1, 4), (3, 4), (3, 2)),
        "system": "RelativeCoordinateSystem",
    }
    coordinates_metadata_dict = coordinates_metadata.to_dict()
    assert coordinates_metadata_dict == expected_schema
    assert CoordinatesMetadata.from_dict(coordinates_metadata_dict) == coordinates_metadata


def test_element_to_dict():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    element = Element(
        element_id="awt32t1",
        coordinates=coordinates,
        coordinate_system=coordinate_system,
    )

    assert element.to_dict() == {
        "metadata": {
            "coordinates": {
                "layout_height": 1,
                "layout_width": 1,
                "points": ((1, 2), (1, 4), (3, 4), (3, 2)),
                "system": "RelativeCoordinateSystem",
            },
        },
        "type": None,
        "text": "",
        "element_id": "awt32t1",
    }


def test_regex_metadata_round_trips_through_JSON():
    """metadata.regex_metadata should appear at full depth in JSON."""
    regex_metadata = {
        "mail-stop": [RegexMetadata(text="MS-107", start=18, end=24)],
        "version": [
            RegexMetadata(text="current=v1.7.2", start=7, end=21),
            RegexMetadata(text="supersedes=v1.7.2", start=22, end=40),
        ],
    }
    metadata = ElementMetadata(regex_metadata=regex_metadata)

    metadata_json = json.dumps(metadata.to_dict())
    deserialized_metadata = ElementMetadata.from_dict(json.loads(metadata_json))
    reserialized_metadata_json = json.dumps(deserialized_metadata.to_dict())

    assert reserialized_metadata_json == metadata_json


class DescribeElementMetadata:
    """Unit-test suite for `unstructured.documents.elements.ElementMetadata`."""

    # -- It can be constructed with known keyword arguments. In particular, including a non-known
    # -- keyword argument produces a type-error at development time and raises an exception at
    # -- runtime. This catches typos before they reach production.

    def it_detects_unknown_constructor_args_at_both_development_time_and_runtime(self):
        with pytest.raises(TypeError, match="got an unexpected keyword argument 'file_name'"):
            ElementMetadata(file_name="memo.docx")  # pyright: ignore[reportCallIssue]

    @pytest.mark.parametrize(
        "file_path",
        [
            pathlib.Path("documents/docx") / "memos" / "memo-2023-11-10.docx",
            "documents/docx/memos/memo-2023-11-10.docx",
        ],
    )
    def it_accommodates_either_a_pathlib_Path_or_str_for_its_filename_arg(
        self, file_path: pathlib.Path | str
    ):
        meta = ElementMetadata(filename=file_path)

        assert meta.file_directory == "documents/docx/memos"
        assert meta.filename == "memo-2023-11-10.docx"

    def it_leaves_both_filename_and_file_directory_None_when_neither_is_specified(self):
        meta = ElementMetadata()

        assert meta.file_directory is None
        assert meta.filename is None

    @pytest.mark.parametrize("file_path", [pathlib.Path("memo.docx"), "memo.docx"])
    def and_it_leaves_file_directory_None_when_not_specified_and_filename_is_not_a_path(
        self, file_path: pathlib.Path | str
    ):
        meta = ElementMetadata(filename=file_path)

        assert meta.file_directory is None
        assert meta.filename == "memo.docx"

    def and_it_splits_off_directory_path_from_its_filename_arg_when_it_is_a_file_path(self):
        meta = ElementMetadata(filename="documents/docx/memo-2023-11-11.docx")

        assert meta.file_directory == "documents/docx"
        assert meta.filename == "memo-2023-11-11.docx"

    def but_it_prefers_a_specified_file_directory_when_filename_also_contains_a_path(self):
        meta = ElementMetadata(filename="tmp/staging/memo.docx", file_directory="documents/docx")

        assert meta.file_directory == "documents/docx"
        assert meta.filename == "memo.docx"

    # -- It knows the types of its known members so type-checking support is available. --

    def it_knows_the_types_of_its_known_members_so_type_checking_support_is_available(self):
        ElementMetadata(
            category_depth="2",  # pyright: ignore[reportArgumentType]
            file_directory=True,  # pyright: ignore[reportArgumentType]
            text_as_html=42,  # pyright: ignore[reportArgumentType]
        )
        # -- it does not check types at runtime however (choosing to avoid validation overhead) --

    # -- It only stores a field's value when it is not None. --

    def it_returns_the_value_of_an_attribute_it_has(self):
        meta = ElementMetadata(url="https://google.com")
        assert "url" in meta.__dict__
        assert meta.url == "https://google.com"

    def and_it_returns_None_for_a_known_attribute_it_does_not_have(self):
        meta = ElementMetadata()
        assert "url" not in meta.__dict__
        assert meta.url is None

    def but_it_raises_AttributeError_for_an_unknown_attribute_it_does_not_have(self):
        meta = ElementMetadata()
        assert "coefficient" not in meta.__dict__
        with pytest.raises(AttributeError, match="object has no attribute 'coefficient'"):
            meta.coefficient

    def it_stores_a_non_None_field_value_when_assigned(self):
        meta = ElementMetadata()
        assert "file_directory" not in meta.__dict__
        meta.file_directory = "tmp/"
        assert "file_directory" in meta.__dict__
        assert meta.file_directory == "tmp/"

    def it_removes_a_field_when_None_is_assigned_to_it(self):
        meta = ElementMetadata(file_directory="tmp/")
        assert "file_directory" in meta.__dict__
        assert meta.file_directory == "tmp/"

        meta.file_directory = None
        assert "file_directory" not in meta.__dict__
        assert meta.file_directory is None

    # -- It can serialize itself to a dict -------------------------------------------------------

    def it_can_serialize_itself_to_a_dict(self):
        meta = ElementMetadata(
            category_depth=1,
            file_directory="tmp/",
            page_number=2,
            text_as_html="<table></table>",
            url="https://google.com",
        )
        assert meta.to_dict() == {
            "category_depth": 1,
            "file_directory": "tmp/",
            "page_number": 2,
            "text_as_html": "<table></table>",
            "url": "https://google.com",
        }

    def and_it_serializes_a_coordinates_sub_object_to_a_dict_when_it_is_present(self):
        meta = ElementMetadata(
            category_depth=1,
            coordinates=CoordinatesMetadata(
                points=((2, 2), (1, 4), (3, 4), (3, 2)),
                system=RelativeCoordinateSystem(),
            ),
            page_number=2,
        )
        assert meta.to_dict() == {
            "category_depth": 1,
            "coordinates": {
                "layout_height": 1,
                "layout_width": 1,
                "points": ((2, 2), (1, 4), (3, 4), (3, 2)),
                "system": "RelativeCoordinateSystem",
            },
            "page_number": 2,
        }

    def and_it_serializes_a_data_source_sub_object_to_a_dict_when_it_is_present(self):
        meta = ElementMetadata(
            category_depth=1,
            data_source=DataSourceMetadata(
                url="https://www.nih.gov/about-nih/who-we-are/nih-director",
                date_created="2023-11-09",
            ),
            page_number=2,
        )
        assert meta.to_dict() == {
            "category_depth": 1,
            "data_source": {
                "url": "https://www.nih.gov/about-nih/who-we-are/nih-director",
                "date_created": "2023-11-09",
            },
            "page_number": 2,
        }

    def and_it_serializes_an_orig_elements_sub_object_to_base64_when_it_is_present(self):
        elements = assign_hash_ids([Title("Lorem"), Text("Lorem Ipsum")])
        meta = ElementMetadata(
            category_depth=1,
            orig_elements=elements,
            page_number=2,
        )

        assert meta.to_dict() == {
            "category_depth": 1,
            "orig_elements": (
                "eJyFzcsKwjAQheFXKVm7MGkzbXwDocu6EpFcTqTQG3UEtfTdbZa"
                "6cTnDd/jPi0CHHgNf2yAOmXCljjqXoErKoIw3hqJRXlPuyphrEr"
                "tM9GAbLNvNL+t2M56ctvU4o0+AXxPSo2m5g9jIb6VwBE0VBSujp"
                "1LJ6EiRLpwiSBf3fyvZcbo/vlqnwVvGbZzbN0KT7Hr5AG/eQyM="
            ),
            "page_number": 2,
        }

    def but_unlike_in_ElementMetadata_unknown_fields_in_sub_objects_are_ignored(self):
        """Metadata sub-objects ignore fields they do not explicitly define.

        This is _not_ the case for ElementMetadata itself where an non-known field is welcomed as a
        user-defined ad-hoc metadata field.
        """
        element_metadata = {
            "new_field": "hello",
            "data_source": {
                "new_field": "world",
            },
            "coordinates": {
                "new_field": "foo",
            },
        }

        metadata = ElementMetadata.from_dict(element_metadata)
        metadata_dict = metadata.to_dict()

        assert "new_field" in metadata_dict
        assert "new_field" not in metadata_dict["coordinates"]
        assert "new_field" not in metadata_dict["data_source"]

    # -- It can deserialize itself from a dict ---------------------------------------------------

    def it_can_deserialize_itself_from_a_dict(self):
        meta_dict = {
            "category_depth": 1,
            "coefficient": 0.58,
            "coordinates": {
                "layout_height": 4,
                "layout_width": 2,
                "points": ((1, 2), (1, 4), (3, 4), (3, 2)),
                "system": "RelativeCoordinateSystem",
            },
            "data_source": {
                "url": "https://www.nih.gov/about-nih/who-we-are/nih-director",
                "date_created": "2023-11-09",
            },
            "languages": ["eng"],
        }

        meta = ElementMetadata.from_dict(meta_dict)

        # -- known fields present in dict are present in meta --
        assert meta.category_depth == 1

        # -- known sub-object fields present in dict are present in meta --
        assert meta.coordinates == CoordinatesMetadata(
            points=((1, 2), (1, 4), (3, 4), (3, 2)),
            system=RelativeCoordinateSystem(),
        )
        assert meta.data_source == DataSourceMetadata(
            url="https://www.nih.gov/about-nih/who-we-are/nih-director",
            date_created="2023-11-09",
        )

        # -- known fields absent from dict report None but are not present in meta --
        assert meta.file_directory is None
        assert "file_directory" not in meta.__dict__

        # -- non-known fields present in dict are present in meta (we have no way to tell whether
        # -- they are "ad-hoc" or not because we lack indication of user-intent)
        assert meta.coefficient == 0.58

        # -- ad-hoc fields absent from dict raise on attempted access --
        with pytest.raises(AttributeError, match="ntMetadata' object has no attribute 'quotient'"):
            meta.quotient

        # -- but that can be worked around by end-user --
        assert (meta.quotient if hasattr(meta, "quotient") else None) is None

        # -- mutating a mutable (collection) field does not affect the original value --
        assert isinstance(meta.languages, list)
        assert meta.languages == ["eng"]
        meta.languages.append("spa")
        assert meta.languages == ["eng", "spa"]
        assert meta_dict["languages"] == ["eng"]

    # -- It allows downstream users to add an arbitrary new member by assignment. ----------------

    def it_allows_an_end_user_to_add_an_arbitrary_field(self):
        meta = ElementMetadata()
        meta.foobar = 7
        assert "foobar" in meta.__dict__
        assert meta.foobar == 7

    def and_fields_so_added_appear_in_the_metadata_JSON(self):
        meta = ElementMetadata()
        meta.foobar = 7
        assert meta.to_dict() == {"foobar": 7}

    def and_it_removes_an_end_user_field_when_it_is_assigned_None(self):
        meta = ElementMetadata()
        meta.foobar = 7
        assert "foobar" in meta.__dict__
        meta.foobar = None
        assert "foobar" not in meta.__dict__
        with pytest.raises(
            AttributeError, match="'ElementMetadata' object has no attribute 'foobar'"
        ):
            meta.foobar

    # -- It can update itself from another instance ----------------------------------------------

    def it_can_update_itself_from_another_instance(self):
        meta = ElementMetadata(category_depth=1, page_number=1)
        meta.coefficient = 0.58
        meta.stem_length = 18
        other = ElementMetadata(file_directory="tmp/", page_number=2)
        other.quotient = 1.4
        other.stem_length = 20

        meta.update(other)

        # -- known-fields present on self but not other are unchanged --
        assert meta.category_depth == 1
        # -- known-fields present on other but not self are added --
        assert meta.file_directory == "tmp/"
        # -- known-fields present on both self and other are updated --
        assert meta.page_number == 2
        # -- ad-hoc-fields present on self but not other are unchanged --
        assert meta.coefficient == 0.58
        # -- ad-hoc-fields present on other but not self are added --
        assert meta.quotient == 1.4
        # -- ad-hoc-fields present on both self and other are updated --
        assert meta.stem_length == 20
        # -- other is left unchanged --
        assert other.category_depth is None
        assert other.file_directory == "tmp/"
        assert other.page_number == 2
        assert other.text_as_html is None
        assert other.url is None
        assert other.quotient == 1.4
        assert other.stem_length == 20
        with pytest.raises(AttributeError, match="etadata' object has no attribute 'coefficient'"):
            other.coefficient

    def but_it_raises_on_attempt_to_update_from_a_non_ElementMetadata_object(self):
        meta = ElementMetadata()
        with pytest.raises(ValueError, match=r"ate\(\)' must be an instance of 'ElementMetadata'"):
            meta.update({"coefficient": "0.56"})  # pyright: ignore[reportArgumentType]

    # -- It knows when it is equal to another instance -------------------------------------------

    def it_is_equal_to_another_instance_with_the_same_known_field_values(self):
        meta = ElementMetadata(
            category_depth=1,
            coordinates=CoordinatesMetadata(
                points=((1, 2), (1, 4), (3, 4), (3, 2)),
                system=RelativeCoordinateSystem(),
            ),
            data_source=DataSourceMetadata(
                url="https://www.nih.gov/about-nih/who-we-are/nih-director",
                date_created="2023-11-08",
            ),
            file_directory="tmp/",
            languages=["eng"],
            page_number=2,
            text_as_html="<table></table>",
            url="https://google.com",
        )
        assert meta == ElementMetadata(
            category_depth=1,
            coordinates=CoordinatesMetadata(
                points=((1, 2), (1, 4), (3, 4), (3, 2)),
                system=RelativeCoordinateSystem(),
            ),
            data_source=DataSourceMetadata(
                url="https://www.nih.gov/about-nih/who-we-are/nih-director",
                date_created="2023-11-08",
            ),
            file_directory="tmp/",
            languages=["eng"],
            page_number=2,
            text_as_html="<table></table>",
            url="https://google.com",
        )

    def but_it_is_never_equal_to_a_non_ElementMetadata_object(self):
        class NotElementMetadata:
            pass

        meta = ElementMetadata()
        other = NotElementMetadata()

        # -- all the "fields" are the same --
        assert meta.__dict__ == other.__dict__
        # -- but it is rejected solely because its type is different --
        assert meta != other

    def it_is_equal_to_another_instance_with_the_same_ad_hoc_field_values(self):
        meta = ElementMetadata(category_depth=1)
        meta.coefficient = 0.58
        other = ElementMetadata(category_depth=1)
        other.coefficient = 0.58

        assert meta == other

    def but_it_is_not_equal_to_an_instance_with_ad_hoc_fields_that_differ(self):
        meta = ElementMetadata(category_depth=1)
        meta.coefficient = 0.58
        other = ElementMetadata(category_depth=1)
        other.coefficient = 0.72

        assert meta != other

    def it_is_not_equal_when_a_list_field_contains_different_items(self):
        meta = ElementMetadata(languages=["eng"])
        assert meta != ElementMetadata(languages=["eng", "spa"])

    def and_it_is_not_equal_when_the_coordinates_sub_object_field_differs(self):
        meta = ElementMetadata(
            coordinates=CoordinatesMetadata(
                points=((1, 2), (1, 4), (3, 4), (3, 2)),
                system=RelativeCoordinateSystem(),
            )
        )
        assert meta != ElementMetadata(
            coordinates=CoordinatesMetadata(
                points=((2, 2), (2, 4), (3, 4), (4, 2)),
                system=RelativeCoordinateSystem(),
            )
        )

    def and_it_is_not_equal_when_the_data_source_sub_object_field_differs(self):
        meta = ElementMetadata(
            data_source=DataSourceMetadata(
                url="https://www.nih.gov/about-nih/who-we-are/nih-director",
                date_created="2023-11-08",
            )
        )
        assert meta != ElementMetadata(
            data_source=DataSourceMetadata(
                url="https://www.nih.gov/about-nih/who-we-are/nih-director",
                date_created="2023-11-09",
            )
        )

    # -- There is a consolidation-strategy for all known fields ----------------------------------

    def it_can_find_the_consolidation_strategy_for_each_of_its_known_fields(self):
        metadata = ElementMetadata()
        metadata_field_names = sorted(metadata._known_field_names)
        consolidation_strategies = ConsolidationStrategy.field_consolidation_strategies()

        for field_name in metadata_field_names:
            assert field_name in consolidation_strategies, (
                f"ElementMetadata field `.{field_name}` does not have a consolidation strategy."
                f" Add one in `ConsolidationStrategy.field_consolidation_strategies()."
            )


def test_hash_ids_are_unique_for_duplicate_elements():
    # GIVEN
    parent = Text(text="Parent", metadata=ElementMetadata(page_number=1))
    elements = [
        parent,
        Text(text="Element", metadata=ElementMetadata(page_number=1, parent_id=parent.id)),
        Text(text="Element", metadata=ElementMetadata(page_number=1, parent_id=parent.id)),
    ]

    # WHEN
    updated_elements = assign_and_map_hash_ids(copy.deepcopy(elements))
    ids = [element.id for element in updated_elements]

    # THEN
    assert len(ids) == len(set(ids)), "Recalculated IDs must be unique."
    assert elements[1].metadata.parent_id == elements[2].metadata.parent_id

    for idx, updated_element in enumerate(updated_elements):
        assert updated_element.id != elements[idx].id, "IDs haven't changed after recalculation"
        if updated_element.metadata.parent_id is not None:
            assert updated_element.metadata.parent_id in ids, "Parent ID not in the list of IDs"
            assert (
                updated_element.metadata.parent_id != elements[idx].metadata.parent_id
            ), "Parent ID hasn't changed after recalculation"


def test_hash_ids_are_deterministic():
    parent = Text(text="Parent", metadata=ElementMetadata(page_number=1))
    elements = [
        parent,
        Text(text="Element", metadata=ElementMetadata(page_number=1, parent_id=parent.id)),
        Text(text="Element", metadata=ElementMetadata(page_number=1, parent_id=parent.id)),
    ]

    updated_elements = assign_and_map_hash_ids(elements)
    ids = [element.id for element in updated_elements]
    parent_ids = [element.metadata.parent_id for element in updated_elements]

    assert ids == [
        "ea9eb7e80383c190f8cafce1ad666624",
        "4112a8d24886276e18e759d06956021b",
        "eba84bbe7f03e8b91a1527323040ee3d",
    ]
    assert parent_ids == [
        None,
        "ea9eb7e80383c190f8cafce1ad666624",
        "ea9eb7e80383c190f8cafce1ad666624",
    ]


@pytest.mark.parametrize(
    ("text", "sequence_number", "filename", "page_number", "expected_hash"),
    [
        # -- pdf files support page numbers --
        ("foo", 1, "foo.pdf", 1, "4bb264eb23ceb44cd8fcc5af44f8dc71"),
        ("foo", 2, "foo.pdf", 1, "75fc1de48cf724ec00aa8d1c5a0d3758"),
        # -- txt files don't have a page number --
        ("some text", 0, "some.txt", None, "1a2627b5760c06b1440102f11a1edb0f"),
        ("some text", 1, "some.txt", None, "e3fd10d867c4a1c0264dde40e3d7e45a"),
    ],
)
def test_id_to_hash_calculates(text, sequence_number, filename, page_number, expected_hash):
    element = Text(
        text=text,
        metadata=ElementMetadata(filename=filename, page_number=page_number),
    )
    assert element.id_to_hash(sequence_number) == expected_hash, "Returned ID does not match"
    assert element.id == expected_hash, "ID should be set"


def test_formskeysvalues_reads_saves():
    filename = example_doc_path("test_evaluate_files/unstructured_output/form.json")
    as_read = partition_json(filename=filename)
    tmp_file = io.StringIO()
    json.dump([element.to_dict() for element in as_read], tmp_file)
    tmp_file.seek(0)
    as_read_2 = partition_json(file=tmp_file)
    assert as_read == as_read_2
