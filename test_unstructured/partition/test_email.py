"""Test suite for `unstructured.partition.email` module."""

from __future__ import annotations

import datetime
import email
import os
import pathlib
import tempfile
from email import policy
from email.message import EmailMessage
from typing import cast

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import (
    LogCaptureFixture,
    assert_round_trips_through_JSON,
    example_doc_path,
    parse_optional_datetime,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Image,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.documents.email_elements import (
    MetaData,
    ReceivedInfo,
    Recipient,
    Sender,
    Subject,
)
from unstructured.partition.email import (
    convert_to_iso_8601,
    extract_attachment_info,
    partition_email,
    partition_email_header,
)
from unstructured.partition.text import partition_text

EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

IMAGE_EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    NarrativeText(text="hello this is our logo."),
    Image(text="unstructured_logo.png"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

RECEIVED_HEADER_OUTPUT = [
    ReceivedInfo(name="ABCDEFG-000.ABC.guide", text="00.0.0.00"),
    ReceivedInfo(name="ABCDEFG-000.ABC.guide", text="ba23::58b5:2236:45g2:88h2"),
    ReceivedInfo(
        name="received_datetimetz",
        text="2023-02-20 10:03:18+12:00",
        datestamp=datetime.datetime(
            2023,
            2,
            20,
            10,
            3,
            18,
            tzinfo=datetime.timezone(datetime.timedelta(seconds=43200)),
        ),
    ),
    MetaData(name="MIME-Version", text="1.0"),
    MetaData(name="Date", text="Fri, 16 Dec 2022 17:04:16 -0500"),
    Recipient(name="Hello", text="hello@unstructured.io"),
    MetaData(
        name="Message-ID",
        text="CADc-_xaLB2FeVQ7mNsoX+NJb_7hAJhBKa_zet-rtgPGenj0uVw@mail.gmail.com",
    ),
    Subject(text="Test Email"),
    Sender(name="Matthew Robinson", text="mrobinson@unstructured.io"),
    Recipient(name="Matthew Robinson", text="mrobinson@unstructured.io"),
    Recipient(name="Fake Email", text="fake-email@unstructured.io"),
    Recipient(name="test", text="test@unstructured.io"),
    MetaData(
        name="Content-Type",
        text='multipart/alternative; boundary="00000000000095c9b205eff92630"',
    ),
]

HEADER_EXPECTED_OUTPUT = [
    MetaData(name="MIME-Version", text="1.0"),
    MetaData(name="Date", text="Fri, 16 Dec 2022 17:04:16 -0500"),
    MetaData(
        name="Message-ID",
        text="CADc-_xaLB2FeVQ7mNsoX+NJb_7hAJhBKa_zet-rtgPGenj0uVw@mail.gmail.com",
    ),
    Subject(text="Test Email"),
    Sender(name="Matthew Robinson", text="mrobinson@unstructured.io"),
    Recipient(name="Matthew Robinson", text="mrobinson@unstructured.io"),
    MetaData(
        name="Content-Type",
        text='multipart/alternative; boundary="00000000000095c9b205eff92630"',
    ),
]

ALL_EXPECTED_OUTPUT = HEADER_EXPECTED_OUTPUT + EXPECTED_OUTPUT

ATTACH_EXPECTED_OUTPUT = [
    {"filename": "fake-attachment.txt", "payload": b"Hey this is a fake attachment!"},
]


def test_partition_email_from_filename():
    elements = partition_email(filename=example_doc_path("eml/fake-email.eml"))

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-email.eml"


def test_partition_email_from_filename_malformed_encoding():
    elements = partition_email(filename=example_doc_path("eml/fake-email-malformed-encoding.eml"))

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


@pytest.mark.parametrize(
    ("filename", "expected_output"),
    [
        ("fake-email-utf-16.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-be.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-le.eml", EXPECTED_OUTPUT),
        ("fake-email-b64.eml", EXPECTED_OUTPUT),
        ("email-no-utf8-2008-07-16.062410.eml", None),
        ("email-no-utf8-2014-03-17.111517.eml", None),
        ("email-replace-mime-encodings-error-1.eml", None),
        ("email-replace-mime-encodings-error-2.eml", None),
        ("email-replace-mime-encodings-error-3.eml", None),
        ("email-replace-mime-encodings-error-4.eml", None),
        ("email-replace-mime-encodings-error-5.eml", None),
    ],
)
def test_partition_email_from_filename_default_encoding(
    filename: str, expected_output: Element | None
):
    elements = partition_email(example_doc_path("eml/" + filename))

    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename == filename


def test_partition_email_from_file():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


@pytest.mark.parametrize(
    ("filename", "expected_output"),
    [
        ("fake-email-utf-16.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-be.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-le.eml", EXPECTED_OUTPUT),
        ("fake-email-b64.eml", EXPECTED_OUTPUT),
        ("email-no-utf8-2008-07-16.062410.eml", None),
        ("email-no-utf8-2014-03-17.111517.eml", None),
        ("email-replace-mime-encodings-error-1.eml", None),
        ("email-replace-mime-encodings-error-2.eml", None),
        ("email-replace-mime-encodings-error-3.eml", None),
        ("email-replace-mime-encodings-error-4.eml", None),
        ("email-replace-mime-encodings-error-5.eml", None),
    ],
)
def test_partition_email_from_file_default_encoding(filename: str, expected_output: Element | None):
    with open(example_doc_path("eml/" + filename), "rb") as f:
        elements = partition_email(file=f)

    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_file_rb():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


@pytest.mark.parametrize(
    ("filename", "expected_output"),
    [
        ("fake-email-utf-16.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-be.eml", EXPECTED_OUTPUT),
        ("fake-email-utf-16-le.eml", EXPECTED_OUTPUT),
        ("email-no-utf8-2008-07-16.062410.eml", None),
        ("email-no-utf8-2014-03-17.111517.eml", None),
        ("email-replace-mime-encodings-error-1.eml", None),
        ("email-replace-mime-encodings-error-2.eml", None),
        ("email-replace-mime-encodings-error-3.eml", None),
        ("email-replace-mime-encodings-error-4.eml", None),
        ("email-replace-mime-encodings-error-5.eml", None),
    ],
)
def test_partition_email_from_file_rb_default_encoding(
    filename: str, expected_output: Element | None
):
    with open(example_doc_path("eml/" + filename), "rb") as f:
        elements = partition_email(file=f)

    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_spooled_temp_file():
    filename = example_doc_path("eml/family-day.eml")
    with open(filename, "rb") as test_file:
        spooled_temp_file = tempfile.SpooledTemporaryFile()
        spooled_temp_file.write(test_file.read())
        spooled_temp_file.seek(0)
        elements = partition_email(file=spooled_temp_file)
        assert len(elements) == 9
        assert elements[3].text == "Make sure to RSVP!"


def test_partition_email_from_text_file():
    with open(example_doc_path("eml/fake-email.txt"), "rb") as f:
        elements = partition_email(file=f, content_source="text/plain")

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_file_with_headers():
    with open(example_doc_path("eml/fake-email.txt"), "rb") as f:
        elements = partition_email(file=f, content_source="text/plain", include_headers=True)

    assert len(elements) > 0
    assert elements == ALL_EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_file_max():
    with open(example_doc_path("eml/fake-email.txt"), "rb") as f:
        elements = partition_email(file=f, content_source="text/plain", max_partition=20)

    assert len(elements) == 6


def test_partition_email_from_text_file_raises_value_error():
    with pytest.raises(ValueError), open(example_doc_path("eml/fake-email.txt"), "rb") as f:
        partition_email(file=f, content_source="text/plain", min_partition=1000)


def test_partition_email_from_text():
    with open(example_doc_path("eml/fake-email.eml")) as f:
        text = f.read()

    elements = partition_email(text=text)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_work_with_empty_string():
    assert partition_email(text="") == []


def test_partition_email_from_filename_with_embedded_image():
    elements = partition_email(
        example_doc_path("eml/fake-email-image-embedded.eml"), content_source="text/plain"
    )

    assert len(elements) > 0
    assert elements == IMAGE_EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-email-image-embedded.eml"


def test_partition_email_from_file_with_header():
    with open(example_doc_path("eml/fake-email-header.eml")) as f:
        msg = email.message_from_file(f, policy=policy.default)

    msg = cast(EmailMessage, msg)
    elements = partition_email_header(msg)

    assert len(elements) > 0
    assert elements == RECEIVED_HEADER_OUTPUT
    all(element.metadata.filename is None for element in elements)


def test_extract_email_text_matches_html():
    filename = example_doc_path("eml/fake-email-attachment.eml")
    elements_from_text = partition_email(filename, content_source="text/plain")
    elements_from_html = partition_email(filename, content_source="text/html")

    assert len(elements_from_text) == len(elements_from_html)
    # NOTE(robinson) - checking each individually is necessary because the text/html returns
    # HTMLTitle, HTMLNarrativeText, etc
    for i, element in enumerate(elements_from_text):
        assert element == elements_from_text[i]
        assert element.metadata.filename == "fake-email-attachment.eml"


def test_extract_base64_email_text_matches_html():
    filename = example_doc_path("eml/fake-email-b64.eml")
    elements_from_text = partition_email(filename, content_source="text/plain")
    elements_from_html = partition_email(filename, content_source="text/html")

    assert len(elements_from_text) == len(elements_from_html)
    for i, element in enumerate(elements_from_text):
        assert element == elements_from_text[i]
        assert element.metadata.filename == "fake-email-b64.eml"


def test_partition_email_processes_fake_email_with_header():
    elements = partition_email(example_doc_path("eml/fake-email-header.eml"))

    assert len(elements) > 0
    assert all(element.metadata.filename == "fake-email-header.eml" for element in elements)
    assert all(
        element.metadata.bcc_recipient == ["Hello <hello@unstructured.io>"] for element in elements
    )
    assert all(
        element.metadata.cc_recipient
        == ["Fake Email <fake-email@unstructured.io>", "test@unstructured.io"]
        for element in elements
    )
    assert all(element.metadata.email_message_id is not None for element in elements)


@pytest.mark.parametrize(
    (("time", "expected")),
    [
        ("Thu,  4 May 2023 02:32:49 +0000", "2023-05-04T02:32:49+00:00"),
        ("Thu, 4 May 2023 02:32:49 +0000", "2023-05-04T02:32:49+00:00"),
        ("Thu, 4 May 2023 02:32:49 +0000 (UTC)", "2023-05-04T02:32:49+00:00"),
        ("Thursday 5/3/2023 02:32:49", None),
    ],
)
def test_convert_to_iso_8601(time: str, expected: str | None):
    iso_time = convert_to_iso_8601(time)

    assert iso_time == expected


def test_partition_email_still_works_with_no_content(caplog: LogCaptureFixture):
    elements = partition_email(example_doc_path("eml/email-no-html-content-1.eml"))

    assert len(elements) == 1
    assert elements[0].text.startswith("Hey there")
    assert "text/html was not found. Falling back to text/plain" in caplog.text


def test_partition_email_with_json():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    assert_round_trips_through_JSON(elements)


def test_partition_email_with_pgp_encrypted_message(caplog: LogCaptureFixture):
    elements = partition_email(example_doc_path("eml/fake-encrypted.eml"))

    assert elements == []
    assert "WARNING" in caplog.text
    assert "Encrypted email detected" in caplog.text


def test_partition_email_inline_content_disposition():
    elements = partition_email(
        example_doc_path("eml/email-inline-content-disposition.eml"),
        process_attachments=True,
        attachment_partitioner=partition_text,
    )

    assert isinstance(elements[0], Text)
    assert isinstance(elements[1], Text)


def test_add_chunking_strategy_on_partition_email():
    chunk_elements = partition_email(
        example_doc_path("eml/fake-email.txt"), chunking_strategy="by_title"
    )
    elements = partition_email(example_doc_path("eml/fake-email.txt"))
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


# -- raise error behaviors -----------------------------------------------------------------------


def test_partition_msg_raises_with_no_partitioner():
    with pytest.raises(ValueError):
        partition_email(example_doc_path("eml/fake-email-attachment.eml"), process_attachments=True)


def test_partition_email_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_email()


def test_partition_email_raises_with_too_many_specified():
    with open(example_doc_path("eml/fake-email.eml")) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_email(example_doc_path("eml/fake-email.eml"), text=text)


def test_partition_email_raises_with_invalid_content_type():
    with pytest.raises(ValueError):
        partition_email(example_doc_path("eml/fake-email.eml"), content_source="application/json")


# -- metadata behaviors --------------------------------------------------------------------------


def test_partition_email_from_filename_with_metadata_filename():
    elements = partition_email(example_doc_path("eml/fake-email.eml"), metadata_filename="test")

    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_email_from_filename_has_metadata():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    parent_id = elements[0].metadata.parent_id

    assert len(elements) > 0
    assert (
        elements[0].metadata.to_dict()
        == ElementMetadata(
            coordinates=None,
            filename=example_doc_path("eml/fake-email.eml"),
            last_modified="2022-12-16T17:04:16-05:00",
            page_number=None,
            url=None,
            sent_from=["Matthew Robinson <mrobinson@unstructured.io>"],
            sent_to=["NotMatthew <NotMatthew@notunstructured.com>"],
            subject="Test Email",
            filetype="message/rfc822",
            parent_id=parent_id,
            languages=["eng"],
            email_message_id="CADc-_xaLB2FeVQ7mNsoX+NJb_7hAJhBKa_zet-rtgPGenj0uVw@mail.gmail.com",
        ).to_dict()
    )
    expected_dt = datetime.datetime.fromisoformat("2022-12-16T17:04:16-05:00")
    assert parse_optional_datetime(elements[0].metadata.last_modified) == expected_dt
    for element in elements:
        assert element.metadata.filename == "fake-email.eml"


def test_partition_email_from_filename_exclude_metadata():
    elements = partition_email(
        example_doc_path("eml/fake-email-header.eml"), include_metadata=False
    )

    assert parse_optional_datetime(elements[0].metadata.last_modified) is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_from_text_file_exclude_metadata():
    with open(example_doc_path("eml/fake-email.txt"), "rb") as f:
        elements = partition_email(file=f, content_source="text/plain", include_metadata=False)

    assert parse_optional_datetime(elements[0].metadata.last_modified) is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_from_file_exclude_metadata():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f, include_metadata=False)

    assert parse_optional_datetime(elements[0].metadata.last_modified) is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_metadata_date_from_header(mocker: MockFixture):
    mocker.patch("unstructured.partition.email.get_last_modified_date", return_value=None)
    mocker.patch("unstructured.partition.email.get_last_modified_date_from_file", return_value=None)

    elements = partition_email(example_doc_path("eml/fake-email-attachment.eml"))

    assert elements[0].metadata.last_modified == "2022-12-23T12:08:48-06:00"


def test_partition_email_from_file_custom_metadata_date():
    with open(example_doc_path("eml/fake-email-attachment.eml"), "rb") as f:
        elements = partition_email(file=f, metadata_last_modified="2020-07-05T09:24:28")

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_email_custom_metadata_date():
    elements = partition_email(
        example_doc_path("eml/fake-email-attachment.eml"),
        metadata_last_modified="2020-07-05T09:24:28",
    )

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_eml_add_signature_to_metadata():
    elements = partition_email(example_doc_path("eml/signed-doc.p7s"))

    assert len(elements) == 1
    assert elements[0].text == "This is a test"
    assert elements[0].metadata.signature == "<SIGNATURE>\n"


# -- attachment behaviors ------------------------------------------------------------------------


def test_extract_attachment_info():
    with open(example_doc_path("eml/fake-email-attachment.eml")) as f:
        msg = email.message_from_file(f, policy=policy.default)
        msg = cast(EmailMessage, msg)
    attachment_info = extract_attachment_info(msg)

    assert len(attachment_info) > 0
    assert attachment_info == ATTACH_EXPECTED_OUTPUT


def test_partition_email_odd_attachment_filename():
    elements = partition_email(
        example_doc_path("eml/email-equals-attachment-filename.eml"),
        process_attachments=True,
        attachment_partitioner=partition_text,
    )

    assert elements[1].metadata.filename == "odd=file=name.txt"


def test_partition_email_can_process_attachments(tmp_path: pathlib.Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    filename = example_doc_path("eml/fake-email-attachment.eml")
    with open(filename) as f:
        msg = email.message_from_file(f, policy=policy.default)
        msg = cast(EmailMessage, msg)
    extract_attachment_info(msg, output_dir=str(output_dir))

    attachment_filename = os.path.join(
        output_dir,
        str(ATTACH_EXPECTED_OUTPUT[0]["filename"]),
    )

    mocked_last_modification_date = "0000-00-05T09:24:28"

    attachment_elements = partition_text(
        filename=attachment_filename,
        metadata_filename=attachment_filename,
        metadata_last_modified=mocked_last_modification_date,
    )
    expected_metadata = attachment_elements[0].metadata
    expected_metadata.file_directory = None
    expected_metadata.attached_to_filename = filename

    elements = partition_email(
        filename=filename,
        attachment_partitioner=partition_text,
        process_attachments=True,
        metadata_last_modified=mocked_last_modification_date,
    )

    # This test does not need to validate if hierarchy is working
    # Patch to nullify parent_id
    expected_metadata.parent_id = None
    elements[-1].metadata.parent_id = None

    assert elements[0].text.startswith("Hello!")
    for element in elements[:-1]:
        assert element.metadata.filename == "fake-email-attachment.eml"
        assert element.metadata.subject == "Fake email with attachment"
    assert elements[-1].text == "Hey this is a fake attachment!"
    assert elements[-1].metadata == expected_metadata


def test_partition_email_can_process_min_max_with_attachments(tmp_path: pathlib.Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    filename = example_doc_path("eml/fake-email-attachment.eml")
    with open(filename) as f:
        msg = email.message_from_file(f, policy=policy.default)
        msg = cast(EmailMessage, msg)
    extract_attachment_info(msg, output_dir=str(output_dir))

    attachment_filename = str(
        os.path.join(
            output_dir,
            str(ATTACH_EXPECTED_OUTPUT[0]["filename"]),
        )
    )

    attachment_elements = partition_text(
        filename=attachment_filename,
        metadata_filename=attachment_filename,
        min_partition=6,
        max_partition=12,
    )

    elements = partition_email(
        filename=filename,
        attachment_partitioner=partition_text,
        process_attachments=True,
        min_partition=6,
        max_partition=12,
    )

    assert elements[0].text.startswith("Hello!")
    assert elements[-1].text == attachment_elements[-1].text
    assert elements[-2].text == attachment_elements[-2].text
    for element in elements:
        if element.metadata.attached_to_filename is not None:
            assert len(element.text) <= 12
            assert len(element.text) >= 6


# -- language behaviors --------------------------------------------------------------------------


def test_partition_email_element_metadata_has_languages():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))

    assert elements[0].metadata.languages == ["eng"]


def test_partition_email_respects_languages_arg():
    elements = partition_email(example_doc_path("eml/fake-email.eml"), languages=["deu"])

    assert all(element.metadata.languages == ["deu"] for element in elements)


def test_partition_eml_respects_detect_language_per_element():
    elements = partition_email(
        example_doc_path("language-docs/eng_spa_mult.eml"),
        detect_language_per_element=True,
    )
    # languages other than English and Spanish are detected by this partitioner,
    # so this test is slightly different from the other partition tests
    langs = {e.metadata.languages[0] for e in elements if e.metadata.languages is not None}

    assert "eng" in langs
    assert "spa" in langs
