import pytest

from unstructured.metrics.element_type import get_element_type_frequency
from unstructured.partition.auto import partition


@pytest.mark.parametrize(
    ("filename", "frequency"),
    [
        (
            "fake-email.txt",
            {
                "UncategorizedText": [("None", 6)],
                "FigureCaption": [],
                "Figure": [],
                "Text": [],
                "NarrativeText": [("None", 2)],
                "ListItem": [("None", 12)],
                "BulletedText": [],
                "Title": [("None", 5)],
                "Address": [],
                "EmailAddress": [],
                "Image": [],
                "PageBreak": [],
                "Table": [],
                "Header": [],
                "Footer": [],
                "Caption": [],
                "Footnote": [],
                "Formula": [],
                "List-item": [],
                "Page-footer": [],
                "Page-header": [],
                "Picture": [],
                "Section-header": [],
                "Headline": [],
                "Subheadline": [],
                "Abstract": [],
                "Threading": [],
                "Form": [],
                "Field-Name": [],
                "Value": [],
                "Link": [],
            },
        ),
        (
            "sample-presentation.pptx",
            {
                "UncategorizedText": [],
                "FigureCaption": [],
                "Figure": [],
                "Text": [],
                "NarrativeText": [("0", 3)],
                "ListItem": [("0", 6), ("1", 6), ("2", 3)],
                "BulletedText": [],
                "Title": [("0", 4), ("1", 1)],
                "Address": [],
                "EmailAddress": [],
                "Image": [],
                "PageBreak": [],
                "Table": [("None", 1)],
                "Header": [],
                "Footer": [],
                "Caption": [],
                "Footnote": [],
                "Formula": [],
                "List-item": [],
                "Page-footer": [],
                "Page-header": [],
                "Picture": [],
                "Section-header": [],
                "Headline": [],
                "Subheadline": [],
                "Abstract": [],
                "Threading": [],
                "Form": [],
                "Field-Name": [],
                "Value": [],
                "Link": [],
            },
        ),
    ],
)
def test_get_element_type_frequency(filename, frequency):
    elements = partition(filename=f"example-docs/{filename}")
    elements_freq = get_element_type_frequency(elements)
    assert elements_freq == frequency
