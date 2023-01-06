import email
import os
import pathlib
import pytest

from unstructured.documents.elements import NarrativeText, Title, ListItem
from unstructured.partition.email import partition_email, extract_attachment_info


DIRECTORY = pathlib.Path(__file__).parent.resolve()


EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

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


def test_partition_email_from_file_rb():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "rb") as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        text = f.read()
    elements = partition_email(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


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
