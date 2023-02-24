from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.elements import Element, NoID, Text


def test_text_id():
    text_element = Text(text="hello there!")
    assert text_element.id == "c69509590d81db2f37f9d75480c8efed"


def test_element_defaults_to_blank_id():
    element = Element()
    assert isinstance(element.id, NoID)


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
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")
    with pytest.raises(ValueError):
        text_element.apply(lambda s: 1)
