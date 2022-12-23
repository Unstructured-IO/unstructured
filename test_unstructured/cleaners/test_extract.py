import pytest
import datetime

import unstructured.cleaners.extract as extract

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
    text = "Imran Scotty <Imran.Scotty@npf.gov.nr>"
    assert extract.extract_email_address(text) == ["imran.scotty@npf.gov.nr"]


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


def extract_mapi_id():
    assert extract.extract_mapi_id(EMAIL_META_DATA_INPUT) == ["32.88.5467.123"]


def extract_datetimetz():
    assert extract.extract_datetimetx(EMAIL_META_DATA_INPUT) == datetime.datetime(
        2021, 3, 26, 11, 4, 9, tzinfo=datetime.timezone(datetime.timedelta(seconds=43200))
    )
