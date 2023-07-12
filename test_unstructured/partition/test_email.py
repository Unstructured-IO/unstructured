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
    convert_to_iso_8601,
    extract_attachment_info,
    partition_email,
    partition_email_header,
)
from unstructured.partition.text import partition_text

FILE_DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(FILE_DIRECTORY, "..", "..", "example-docs", "eml")


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
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-email.eml"


def test_partition_email_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    elements = partition_email(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_email_from_filename_malformed_encoding():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-malformed-encoding.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


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
def test_partition_email_from_filename_default_encoding(filename, expected_output):
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    elements = partition_email(filename=filename_path)
    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename == filename


def test_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
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
def test_partition_email_from_file_default_encoding(filename, expected_output):
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    with open(filename_path) as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename, "rb") as f:
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
def test_partition_email_from_file_rb_default_encoding(filename, expected_output):
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    with open(filename_path, "rb") as f:
        elements = partition_email(file=f)
    assert len(elements) > 0
    if expected_output:
        assert elements == expected_output
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.txt")
    with open(filename) as f:
        elements = partition_email(file=f, content_source="text/plain")
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_file_with_headers():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.txt")
    with open(filename) as f:
        elements = partition_email(file=f, content_source="text/plain", include_headers=True)
    assert len(elements) > 0
    assert elements == ALL_EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
        text = f.read()
    elements = partition_email(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_text_work_with_empty_string():
    assert partition_email(text="") == []


def test_partition_email_from_filename_with_embedded_image():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-image-embedded.eml")
    elements = partition_email(filename=filename, content_source="text/plain")
    assert len(elements) > 0
    assert elements == IMAGE_EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-email-image-embedded.eml"


def test_partition_email_from_file_with_header():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-header.eml")
    with open(filename) as f:
        msg = email.message_from_file(f)
    elements = partition_email_header(msg)
    assert len(elements) > 0
    assert elements == RECEIVED_HEADER_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_email_from_filename_has_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-header.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    assert (
        elements[0].metadata.to_dict()
        == ElementMetadata(
            coordinates=None,
            filename=filename,
            date="2022-12-16T17:04:16-05:00",
            page_number=None,
            url=None,
            sent_from=["Matthew Robinson <mrobinson@unstructured.io>"],
            sent_to=["Matthew Robinson <mrobinson@unstructured.io>"],
            subject="Test Email",
            filetype="message/rfc822",
        ).to_dict()
    )
    expected_dt = datetime.datetime.fromisoformat("2022-12-16T17:04:16-05:00")
    assert elements[0].metadata.get_date() == expected_dt
    for element in elements:
        assert element.metadata.filename == "fake-email-header.eml"


def test_extract_email_text_matches_html():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-attachment.eml")
    elements_from_text = partition_email(filename=filename, content_source="text/plain")
    elements_from_html = partition_email(filename=filename, content_source="text/html")
    assert len(elements_from_text) == len(elements_from_html)
    # NOTE(robinson) - checking each individually is necessary because the text/html returns
    # HTMLTitle, HTMLNarrativeText, etc
    for i, element in enumerate(elements_from_text):
        assert element == elements_from_text[i]
        assert element.metadata.filename == "fake-email-attachment.eml"


def test_extract_attachment_info():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-attachment.eml")
    with open(filename) as f:
        msg = email.message_from_file(f)
    attachment_info = extract_attachment_info(msg)
    assert len(attachment_info) > 0
    assert attachment_info == ATTACH_EXPECTED_OUTPUT


def test_partition_email_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_email()


def test_partition_email_raises_with_too_many_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
        text = f.read()
    with pytest.raises(ValueError):
        partition_email(filename=filename, text=text)


def test_partition_email_raises_with_invalid_content_type():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with pytest.raises(ValueError):
        partition_email(filename=filename, content_source="application/json")


def test_partition_email_processes_fake_email_with_header():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-header.eml")
    elements = partition_email(filename=filename)
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "fake-email-header.eml"


@pytest.mark.parametrize(
    (("time", "expected")),
    [
        ("Thu,  4 May 2023 02:32:49 +0000", "2023-05-04T02:32:49+00:00"),
        ("Thu, 4 May 2023 02:32:49 +0000", "2023-05-04T02:32:49+00:00"),
        ("Thu, 4 May 2023 02:32:49 +0000 (UTC)", "2023-05-04T02:32:49+00:00"),
        ("Thursday 5/3/2023 02:32:49", None),
    ],
)
def test_convert_to_iso_8601(time, expected):
    iso_time = convert_to_iso_8601(time)
    assert iso_time == expected


def test_partition_email_still_works_with_no_content():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "email-no-html-content-1.eml")
    elements = partition_email(filename=filename)
    assert elements == []


def test_partition_email_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email-header.eml")
    elements = partition_email(filename=filename, include_metadata=False)
    assert elements[0].metadata.get_date() is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_from_text_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.txt")
    with open(filename) as f:
        elements = partition_email(file=f, content_source="text/plain", include_metadata=False)
    assert elements[0].metadata.get_date() is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
        elements = partition_email(file=f, include_metadata=False)
    assert elements[0].metadata.get_date() is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_email_can_process_attachments(
    tmpdir,
    filename="example-docs/eml/fake-email-attachment.eml",
):
    with open(filename) as f:
        msg = email.message_from_file(f)
    extract_attachment_info(msg, output_dir=tmpdir.dirname)
    attachment_filename = os.path.join(tmpdir.dirname, ATTACH_EXPECTED_OUTPUT[0]["filename"])
    attachment_elements = partition_text(
        filename=attachment_filename,
        metadata_filename=attachment_filename,
    )
    expected_metadata = attachment_elements[0].metadata
    expected_metadata.file_directory = None
    expected_metadata.attached_to_filename = filename

    elements = partition_email(
        filename=filename,
        attachment_partitioner=partition_text,
        process_attachments=True,
    )

    assert elements[0].text.startswith("Hello!")

    for element in elements[:-1]:
        assert element.metadata.filename == "fake-email-attachment.eml"
        assert element.metadata.subject == "Fake email with attachment"

    assert elements[-1].text == "Hey this is a fake attachment!"
    assert elements[-1].metadata == expected_metadata


def test_partition_msg_raises_with_no_partitioner(
    filename="example-docs/eml/fake-email-attachment.eml",
):
    with pytest.raises(ValueError):
        partition_email(filename=filename, process_attachments=True)
