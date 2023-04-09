import datetime
import email
import os
import pathlib

import pytest

from unstructured.documents.elements import (
    ElementMetadata,
    Image,
    ListItem,
    NarrativeText,
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
    extract_attachment_info,
    partition_email,
    partition_email_header,
)

DIRECTORY = pathlib.Path(__file__).parent.resolve()


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
    MetaData(
        name="Message-ID",
        text="<CADc-_xaLB2FeVQ7mNsoX+NJb_7hAJhBKa_zet-rtgPGenj0uVw@mail.gmail.com>",
    ),
    Subject(text="Test Email"),
    Sender(name="Matthew Robinson", text="mrobinson@unstructured.io"),
    Recipient(name="Matthew Robinson", text="mrobinson@unstructured.io"),
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
        text="<CADc-_xaLB2FeVQ7mNsoX+NJb_7hAJhBKa_zet-rtgPGenj0uVw@mail.gmail.com>",
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
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename) as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_file_rb():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "rb") as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.txt")
    with open(filename) as f:
        elements = partition_email(file=f, content_source="text/plain")
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text_file_with_headers():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.txt")
    with open(filename) as f:
        elements = partition_email(file=f, content_source="text/plain", include_headers=True)
    assert len(elements) > 0
    assert elements == ALL_EXPECTED_OUTPUT


def test_partition_email_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename) as f:
        text = f.read()
    elements = partition_email(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text_work_with_empty_string():
    assert partition_email(text="") == []


def test_partition_email_from_filename_with_embedded_image():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-image-embedded.eml")
    elements = partition_email(filename=filename, content_source="text/plain")
    assert len(elements) > 0
    assert elements == IMAGE_EXPECTED_OUTPUT


def test_partition_email_header():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-header.eml")
    with open(filename) as f:
        msg = email.message_from_file(f)
    elements = partition_email_header(msg)
    assert len(elements) > 0
    assert elements == RECEIVED_HEADER_OUTPUT


def test_partition_email_has_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-header.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert elements[0].metadata == ElementMetadata(
        filename=filename,
        date="2022-12-16T17:04:16-05:00",
        page_number=None,
        url=None,
        sent_from=["Matthew Robinson <mrobinson@unstructured.io>"],
        sent_to=["Matthew Robinson <mrobinson@unstructured.io>"],
        subject="Test Email",
    )


def test_extract_email_text_matches_html():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-attachment.eml")
    elements_from_text = partition_email(filename=filename, content_source="text/plain")
    elements_from_html = partition_email(filename=filename, content_source="text/html")

    assert len(elements_from_text) == len(elements_from_html)
    # NOTE(robinson) - checking each individually is necessary because the text/html returns
    # HTMLTitle, HTMLNarrativeText, etc
    for i, element in enumerate(elements_from_text):
        assert element == elements_from_text[i]


def test_extract_attachment_info():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-attachment.eml")
    with open(filename) as f:
        msg = email.message_from_file(f)
    attachment_info = extract_attachment_info(msg)
    assert len(attachment_info) > 0
    assert attachment_info == ATTACH_EXPECTED_OUTPUT


def test_partition_email_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_email()


def test_partition_email_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_email(filename=filename, text=text)


def test_partition_email_raises_with_invalid_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with pytest.raises(ValueError):
        partition_email(filename=filename, content_source="application/json")


def test_partition_email_processes_fake_email_with_header():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-header.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
