import os
import pathlib

from unstructured.documents.elements import NarrativeText, Title, ListItem
from unstructured.partition.auto import partition

EXAMPLE_DOCS_DIRECTORY = pathlib.Path(__file__).parent.resolve()


EXPECTED_EMAIL_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_auto_partition_email_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    elements = partition(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    with open(filename, "r") as f:
        elements = partition(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
