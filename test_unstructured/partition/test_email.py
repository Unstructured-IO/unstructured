import email
import os
import pathlib
import pytest

from unstructured.documents.elements import NarrativeText, Title, ListItem
from unstructured.documents.email_elements import (
    MetaData,
    Recipient,
    Sender,
    Subject,
)
from unstructured.partition.email import extract_attachment_info, partition_email, partition_header


DIRECTORY = pathlib.Path(__file__).parent.resolve()


EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
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
        name="Content-Type", text='multipart/alternative; boundary="00000000000095c9b205eff92630"'
    ),
]

ALL_EXPECTED_OUTPUT = (EXPECTED_OUTPUT, HEADER_EXPECTED_OUTPUT)

ATTACH_EXPECTED_OUTPUT = [
    {"filename": "fake-attachment.txt", "payload": b"Hey this is a fake attachment!"}
]


def test_partition_email_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.txt")
    with open(filename, "r") as f:
        elements = partition_email(file=f, content_source="text/plain")
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text_file_with_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.txt")
    with open(filename, "r") as f:
        elements = partition_email(file=f, content_source="text/plain", get_meta_data=True)
    assert len(elements) > 0
    assert elements == ALL_EXPECTED_OUTPUT


def test_partition_email_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        text = f.read()
    elements = partition_email(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_header():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        msg = email.message_from_file(f)
    elements = partition_header(msg)
    assert len(elements) > 0
    assert elements == HEADER_EXPECTED_OUTPUT


def test_extract_attachment_info():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-attachment.eml")
    with open(filename, "r") as f:
        msg = email.message_from_file(f)
    attachment_info = extract_attachment_info(msg)
    assert len(attachment_info) > 0
    assert attachment_info == ATTACH_EXPECTED_OUTPUT


def test_partition_email_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_email()


def test_partition_email_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_email(filename=filename, text=text)


def test_partition_email_raises_with_invalid_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with pytest.raises(ValueError):
        partition_email(filename=filename, content_source="application/json")
