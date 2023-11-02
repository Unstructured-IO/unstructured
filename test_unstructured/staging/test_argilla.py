import os

import pytest

from unstructured.documents.elements import NarrativeText, Title

is_in_docker = os.path.exists("/.dockerenv")
if not is_in_docker:
    import argilla as rg

    from unstructured.staging import argilla

    @pytest.fixture()
    def elements():
        return [Title(text="example"), NarrativeText(text="another example")]

    @pytest.mark.parametrize(
        ("task_name", "dataset_type", "extra_kwargs"),
        [
            (
                "text_classification",
                rg.DatasetForTextClassification,
                {"metadata": [{"type": "text1"}, {"type": "text2"}]},
            ),
            (
                "text_classification",
                rg.DatasetForTextClassification,
                {},
            ),
            (
                "token_classification",
                rg.DatasetForTokenClassification,
                {"metadata": [{"type": "text1"}, {"type": "text2"}]},
            ),
            (
                "token_classification",
                rg.DatasetForTokenClassification,
                {},
            ),
            (
                "text2text",
                rg.DatasetForText2Text,
                {"metadata": [{"type": "text1"}, {"type": "text2"}]},
            ),
            (
                "text2text",
                rg.DatasetForText2Text,
                {},
            ),
        ],
    )
    def test_stage_for_argilla(elements, task_name, dataset_type, extra_kwargs):
        argilla_dataset = argilla.stage_for_argilla(elements, task_name, **extra_kwargs)
        assert isinstance(argilla_dataset, dataset_type)
        for record, element in zip(argilla_dataset, elements):
            assert record.text == element.text
            assert record.id == element.id
            for kwarg in extra_kwargs:
                assert getattr(record, kwarg) in extra_kwargs[kwarg]

    @pytest.mark.parametrize(
        ("task_name", "error", "error_message", "extra_kwargs"),
        [
            ("unknown_task", ValueError, "invalid value", {}),
            ("text_classification", ValueError, "invalid value", {"metadata": "invalid metadata"}),
        ],
    )
    def test_invalid_stage_for_argilla(elements, task_name, error, error_message, extra_kwargs):
        with pytest.raises(error) as e:
            argilla.stage_for_argilla(elements, task_name, **extra_kwargs)
            assert error_message in e.args[0].lower() if error_message else True

    @pytest.mark.parametrize(
        ("partition", "file"),
        [
            ("xlsx", "example-docs/stanley-cups.xlsx"),
            ("xls", "example-docs/stanley-cups.xlsx"),
            # Tables without
            ("csv", "example-docs/stanley-cups.csv"),
            ("tsv", "example-docs/stanley-cups.tsv"),
            # Email
            ("msg", "example-docs/fake-email.msg"),
            ("email",  "example-docs/eml/fake-email.eml"),
            # slides
            ("ppt", "example-docs/fake-power-point.ppt"),
            ("pptx", "example-docs/fake-power-point.pptx"),
            # doc with page
            ("doc", "example-docs/fake.doc"),
            ("epub", "example-docs/winter-sports.epub"),
            ("pdf", "example-docs/layout-parser-paper-fast.pdf"),
            # doc without pages
            ("image", "example-docs/layout-parser-paper-fast.jpg"),
            ("md", "README.md"),
            ("odt", "example-docs/fake.odt"),
            ("org", "example-docs/README.org"),
            ("rst", "example-docs/README.rst"),
            ("rtf", "example-docs/fake-doc.rtf"),
            ("text", "example-docs/fake-text.txt")
        ]
    )
    def test_stage_for_argilla_feedback(partition, file):
        argilla_dataset = argilla.get_argilla_feedback_dataset(
            partition_type=partition,
            questions=[rg.LabelQuestion(name="harmful", labels=["yes", "no"])],
            include_defaults=False
        )
        argilla.partition_stage_for_argilla(
            partition_types=partition,
            dataset=argilla_dataset,
            files=[file],
        )

