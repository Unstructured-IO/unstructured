from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.email_elements import EmailElement, Name, NoID, Subject


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

    expected_hash = "5feceb66ffc86f38d952786c6d696c79"
    # -- calling `.id_to_hash()` changes the element's id-type to hash --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash

    # -- `.id_to_hash()` is idempotent --
    assert element.id_to_hash(0) == expected_hash
    assert element.id == expected_hash


@pytest.mark.parametrize(
    "element",
    [
        EmailElement(text=""),  # should default to UUID
        Name(name="Example", text="hello there!"),  # should default to UUID
        Name(name="Example", text="hello there!", element_id=NoID()),
    ],
)
def test_EmailElement_self_assigns_itself_a_UUID_id(element: EmailElement):
    assert isinstance(element.id, str)
    assert len(element.id) == 36
    assert element.id.count("-") == 4


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
