# pyright: reportPrivateUsage=false

"""Test-suite for `unstructured.documents.elements` module."""

from __future__ import annotations

import json
import pathlib
from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.coordinates import (
    CoordinateSystem,
    Orientation,
    RelativeCoordinateSystem,
)
from unstructured.documents.elements import (
    UUID,
    ConsolidationStrategy,
    CoordinatesMetadata,
    DataSourceMetadata,
    Element,
    ElementMetadata,
    NoID,
    Points,
    RegexMetadata,
    Text,
)


def test_text_id():
    text_element = Text(text="hello there!")
    assert text_element.id == "c69509590d81db2f37f9d75480c8efed"


def test_text_uuid():
    text_element = Text(text="hello there!", element_id=UUID())

    id = text_element.id

    assert isinstance(id, str)
    assert len(id) == 36
    assert id.count("-") == 4
    # -- Test that the element is JSON serializable. This shold run without an error --
    json.dumps(text_element.to_dict())


def test_element_defaults_to_blank_id():
    element = Element()
    assert isinstance(element.id, NoID)


def test_element_uuid():
    element = Element(element_id=UUID())
    assert isinstance(element.id, UUID)


def test_text_element_apply_cleaners():
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")

    text_element.apply(partial(clean_prefix, pattern=r"\[\d{1,2}\]"))
    assert str(text_element) == "A Textbook on Crocodile Habitats"


def test_text_element_apply_multiple_cleaners():
    cleaners = [
        partial(clean_prefix, pattern=r"\[\d{1,2}\]"),
        partial(translate_text, target_lang="ru"),
    ]
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")
    text_element.apply(*cleaners)
    assert str(text_element) == "Учебник по крокодильным средам обитания"


def test_apply_raises_if_func_does_not_produce_string():
    def bad_cleaner(s: str):
        return 1

    text_element = Text(text="[1] A Textbook on Crocodile Habitats")

    with pytest.raises(ValueError, match="Cleaner produced a non-string output."):
        text_element.apply(bad_cleaner)  # pyright: ignore[reportGeneralTypeIssues]


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
            ElementMetadata(file_name="memo.docx")  # pyright: ignore[reportGeneralTypeIssues]

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
            category_depth="2",  # pyright: ignore[reportGeneralTypeIssues]
            file_directory=True,  # pyright: ignore[reportGeneralTypeIssues]
            text_as_html=42,  # pyright: ignore[reportGeneralTypeIssues]
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
            meta.update({"coefficient": "0.56"})  # pyright: ignore[reportGeneralTypeIssues]

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
