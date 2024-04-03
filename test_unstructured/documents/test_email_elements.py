from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.email_elements import EmailElement, Name, NoID


def test_text_id():
    name_element = Name(name="Example", text="hello there!")
    assert name_element.id_to_hash(index_in_sequence=0) == "eae4fcad50d11af5cec20276d7d5dc65"


def test_text_id_is_a_string_uuid_by_default():
    def _assert_uuid_like(id_to_test: str) -> None:
        assert isinstance(id_to_test, str)
        assert len(id_to_test) == 36
        assert id_to_test.count("-") == 4

    _assert_uuid_like(EmailElement(text="").id)
    _assert_uuid_like(Name(name="Example", text="hello there!").id)
    _assert_uuid_like(Name(name="Example", text="hello there!", element_id=NoID()).id)


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
