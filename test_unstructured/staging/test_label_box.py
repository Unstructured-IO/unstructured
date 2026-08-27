import builtins
import os

import pytest

from unstructured.documents.elements import NarrativeText, Title
from unstructured.staging import label_box


@pytest.fixture()
def elements():
    return [Title(text="Title 1"), NarrativeText(text="Narrative 1")]


@pytest.fixture()
def output_directory(tmp_path):
    return str(tmp_path)


@pytest.fixture()
def nonexistent_output_directory(tmp_path):
    return os.path.join(str(tmp_path), "nonexistent_dir")


@pytest.fixture()
def url_prefix():
    return "https://storage.googleapis.com/labelbox-sample-datasets/nlp"


@pytest.mark.parametrize(
    ("attachments", "raises_error"),
    [
        (
            [
                {"type": "RAW_TEXT", "value": "Description Text"},
                {"type": "IMAGE", "value": "Image label", "ignored_value": 123},
            ],
            False,
        ),
        ([{"type": "INVALID_TYPE", "value": "Description Text"}], True),
        ([{"type": "RAW_TEXT", "value": 1}], True),
        ([{"type": "RAW_TEXT"}], True),
        ([{"value": "My text label"}], True),
    ],
)
def test_validate_attachments(attachments, raises_error):
    if raises_error:
        with pytest.raises(ValueError):
            label_box._validate_attachments(attachments, 0)
    else:
        label_box._validate_attachments(attachments, 0)


attachment = {"type": "RAW_TEXT", "value": "Text description."}


@pytest.mark.parametrize(
    (
        (
            "external_ids",
            "attachments",
            "output_directory_fixture",
            "create_directory",
            "raises",
            "exception_class",
        )
    ),
    [
        (None, None, "output_directory", True, False, None),
        (["id1", "id2"], None, "output_directory", True, False, None),
        (["id1"], None, "output_directory", True, True, ValueError),
        (None, [[attachment], [attachment]], "output_directory", True, False, None),
        (None, [[attachment]], "output_directory", True, True, ValueError),
        (["id1", "id2"], [[attachment] * 2, [attachment]], "output_directory", True, False, None),
        (
            ["id1", "id2"],
            [[attachment] * 2, [attachment]],
            "nonexistent_output_directory",
            True,
            False,
            None,
        ),
        (
            ["id1", "id2"],
            [[attachment] * 2, [attachment]],
            "nonexistent_output_directory",
            False,
            True,
            FileNotFoundError,
        ),
    ],
)
def test_stage_for_label_box(
    elements,
    url_prefix,
    external_ids,
    attachments,
    output_directory_fixture,
    create_directory,
    raises,
    exception_class,
    request,
):
    output_directory = request.getfixturevalue(output_directory_fixture)
    if raises:
        with pytest.raises(exception_class):
            label_box.stage_for_label_box(
                elements,
                output_directory,
                url_prefix,
                external_ids=external_ids,
                attachments=attachments,
                create_directory=create_directory,
            )
    else:
        config = label_box.stage_for_label_box(
            elements,
            output_directory,
            url_prefix,
            external_ids=external_ids,
            attachments=attachments,
            create_directory=create_directory,
        )
        assert len(config) == len(elements)
        for index, (element_config, element) in enumerate(zip(config, elements)):
            print(element_config)

            if external_ids:
                assert element_config["externalId"] == external_ids[index]
            else:
                assert element_config["externalId"] == element.id

            if attachments:
                assert element_config["attachments"] == [
                    {"type": attachment["type"], "value": attachment["value"]}
                    for attachment in attachments[index]
                ]

            assert element_config["data"].startswith(url_prefix)
            assert element_config["data"].endswith(f"{element_config['externalId']}.txt")

            output_filepath = os.path.join(output_directory, f"{element_config['externalId']}.txt")
            with open(output_filepath, encoding="utf-8") as data_file:
                assert data_file.read().strip() == element.text.strip()


def test_stage_for_label_box_writes_text_files_as_utf8(output_directory, url_prefix, monkeypatch):
    """Element text is staged as UTF-8 rather than in the platform's locale encoding.

    LabelBox reads the staged files as UTF-8, and text outside the locale codec (for example
    ``cp1252`` on Windows, or ASCII under a POSIX/``C`` locale) otherwise raises
    ``UnicodeEncodeError``. Record the encoding each text-mode ``open()`` is given so the
    assertion holds on a UTF-8 platform too.
    """
    text = "Sales figures — 第一季度 café"
    text_mode_encodings = []
    real_open = builtins.open

    def recording_open(file, mode="r", buffering=-1, encoding=None, *args, **kwargs):
        if "b" not in mode:
            text_mode_encodings.append(encoding)
        return real_open(file, mode, buffering, encoding, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recording_open)
    config = label_box.stage_for_label_box(
        [NarrativeText(text=text)], output_directory, url_prefix, create_directory=True
    )
    monkeypatch.undo()

    assert text_mode_encodings == ["utf-8"]

    output_filepath = os.path.join(output_directory, f"{config[0]['externalId']}.txt")
    with open(output_filepath, "rb") as data_file:
        assert data_file.read().decode("utf-8") == text
