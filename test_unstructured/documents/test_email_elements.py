from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.email_elements import EmailElement, Name, Subject


@pytest.mark.parametrize(
    "element", [EmailElement(text=""), Name(text="", name=""), Subject(text="")]
)
def test_EmailElement_autoassigns_a_UUID_then_becomes_an_idempotent_and_deterministic_hash(
    element: EmailElement,
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


def test_Name_should_assign_a_deterministic_and_an_idempotent_hash():
    element = Name(name="Example", text="hello there!")
    expected_hash = "7d191bcecf80c122578c497de5f0dae7"

    assert element._element_id is None, "Element should not have an ID yet"

    # -- calculating hash for the first time --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash

    # -- `.id_to_hash()` is idempotent --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash


@pytest.mark.parametrize(
    "element",
    [
        EmailElement(text=""),  # -- the default `element_id` is None --
        Name(name="Example", text="hello there!"),  # -- the default `element_id` is None --
        Name(name="Example", text="hello there!", element_id=None),
    ],
)
def test_EmailElement_assigns_a_UUID_only_once_and_only_at_the_first_id_request(
    element: EmailElement,
):
    assert element._element_id is None, "Element should not have an ID yet"

    # -- this should generate and assign a fresh UUID --
    id_value = element.id

    # -- check that the UUID is valid --
    assert element._element_id is not None, "Element should already have an ID"
    assert isinstance(id_value, str)
    assert len(id_value) == 36
    assert id_value.count("-") == 4

    assert element.id == id_value, "UUID assignment should happen only once"


def test_text_element_apply_cleaners():
    name_element = Name(name="[2] Example docs", text="[1] A Textbook on Crocodile Habitats")

    name_element.apply(partial(clean_prefix, pattern=r"\[\d{1,2}\]"))
    assert str(name_element) == "Example docs: A Textbook on Crocodile Habitats"


def test_name_element_apply_multiple_cleaners():
    cleaners = [
        partial(clean_prefix, pattern=r"\[\d{1,2}\]"),
        partial(translate_text, target_lang="ru"),
    ]
    name_element = Name(
        name="[1] A Textbook on Crocodile Habitats",
        text="[1] A Textbook on Crocodile Habitats",
    )
    name_element.apply(*cleaners)
    assert (
        str(name_element)
        == "Учебник по крокодильным средам обитания: Учебник по крокодильным средам обитания"
    )


def test_apply_raises_if_func_does_not_produce_string():
    name_element = Name(name="Example docs", text="[1] A Textbook on Crocodile Habitats")
    with pytest.raises(ValueError):
        name_element.apply(lambda s: 1)
