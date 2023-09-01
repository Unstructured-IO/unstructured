import datetime

import pytest

from unstructured.cleaners import extract

EMAIL_META_DATA_INPUT = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""


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


def test_extract_email_address():
    text = "Im Rabn <Im.Rabn@npf.gov.nr>"
    assert extract.extract_email_address(text) == ["im.rabn@npf.gov.nr"]


def test_extract_ip_address():
    assert extract.extract_ip_address(EMAIL_META_DATA_INPUT) == [
        "ba23::58b5:2236:45g2:88h2",
        "ba23::58b5:2236:45g2:88h2%25",
    ]


def test_extract_ip_address_name():
    assert extract.extract_ip_address_name(EMAIL_META_DATA_INPUT) == [
        "ABC.DEF.local",
        "ABC.DEF.local",
    ]


def test_extract_mapi_id():
    assert extract.extract_mapi_id(EMAIL_META_DATA_INPUT) == ["32.88.5467.123"]


def test_extract_datetimetz():
    assert extract.extract_datetimetz(EMAIL_META_DATA_INPUT) == datetime.datetime(
        2021,
        3,
        26,
        11,
        4,
        9,
        tzinfo=datetime.timezone(datetime.timedelta(seconds=43200)),
    )


def test_extract_datetimetz_works_with_no_date():
    assert extract.extract_datetimetz("NO DATE HERE") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("215-867-5309", "215-867-5309"),
        ("Phone Number: +1 215.867.5309", "+1 215.867.5309"),
        ("Phone Number: Just Kidding", ""),
    ],
)
def test_extract_us_phone_number(text, expected):
    phone_number = extract.extract_us_phone_number(text)
    assert phone_number == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1. Introduction:", ("1", None, None)),
        ("a. Introduction:", ("a", None, None)),
        ("20.3 Morse code ●●●", ("20", "3", None)),
        ("5.3.1 Convolutional Networks ", ("5", "3", "1")),
        ("D.b.C Recurrent Neural Networks", ("D", "b", "C")),
        ("2.b.1 Recurrent Neural Networks", ("2", "b", "1")),
        ("eins. Neural Networks", (None, None, None)),
        ("bb.c Feed Forward Neural Networks", ("bb", "c", None)),
        ("aaa.ccc Metrics", (None, None, None)),
        (" version = 3.8", (None, None, None)),
        ("1 2. 3 4", (None, None, None)),
        ("1) 2. 3 4", (None, None, None)),
        ("2,3. Morse code 3. ●●●", (None, None, None)),
        ("1..2.3 four", (None, None, None)),
        ("Fig. 2: The relationship", (None, None, None)),
        ("23 is everywhere", (None, None, None)),
    ],
)
def test_extract_ordered_bullets(text, expected):
    assert extract.extract_ordered_bullets(text=text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "https://my-image.jpg",
            (["https://my-image.jpg"]),
        ),
        (
            "https://my-image.png with some text",
            (["https://my-image.png"]),
        ),
        (
            "https://my-image/with/some/path.png",
            (["https://my-image/with/some/path.png"]),
        ),
        (
            "some text https://my-image.jpg with another http://my-image.bmp",
            (["https://my-image.jpg", "http://my-image.bmp"]),
        ),
        (
            "http://not-an-image.com",
            ([]),
        ),
        (
            "some text",
            ([]),
        ),
        (
            "some text https://my-image.JPG with another http://my-image.BMP",
            (["https://my-image.JPG", "http://my-image.BMP"]),
        ),
        (
            "http://my-path-with-CAPS/my-image.JPG",
            (["http://my-path-with-CAPS/my-image.JPG"]),
        ),
        (
            "http://my-path/my%20image.JPG",
            (["http://my-path/my%20image.JPG"]),
        ),
        # url with reference #
        (
            "https://my-image.jpg#ref",
            (["https://my-image.jpg"]),
        ),
    ],
)
def test_extract_image_urls_from_html(text, expected):
    assert extract.extract_image_urls_from_html(text=text) == expected
