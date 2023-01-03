import pytest

import unstructured.cleaners.extract as extract


def test_get_indexed_match_raises_with_bad_index():
    with pytest.raises(ValueError):
        extract._get_indexed_match("BLAH BLAH BLAH", "BLAH", -1)


def test_get_indexed_match_raises_with_index_too_high():
    with pytest.raises(ValueError):
        extract._get_indexed_match("BLAH BLAH BLAH", "BLAH", 4)


def test_extract_text_before():
    text = "Teacher: BLAH BLAH BLAH; Student: BLAH BLAH BLAH!"
    assert extract.extract_text_before(text, "BLAH", 1) == "Teacher: BLAH"


def test_extract_text_after():
    text = "Teacher: BLAH BLAH BLAH; Student: BLAH BLAH BLAH!"
    assert extract.extract_text_after(text, "BLAH;", 0) == "Student: BLAH BLAH BLAH!"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("215-867-5309", "215-867-5309"),
        ("Phone Number: +1 215.867.5309", "+1 215.867.5309"),
        ("Phone Number: Just Kidding", ""),
    ],
)
def test_extract_us_phone_number(text, expected):
    phone_number = extract.extract_us_phone_number(text)
    assert phone_number == expected
