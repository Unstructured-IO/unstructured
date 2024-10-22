import pytest

from unstructured.partition.html.transformations import remove_empty_tags_from_html_content


@pytest.mark.parametrize(
    ("html_content, expected_output"),  # noqa PT006
    [
        ("<div></div>", ""),
        ("<div><p></p></div>", "<div></div>"),
        ("<div><input/></div>", "<div><input/></div>"),
        ("<div><br/></div>", "<div><br/></div>"),
        ('<div><p id="1"></p></div>', '<div><p id="1"></p></div>'),
        ("<div><p>Content</p></div>", "<div><p>Content</p></div>"),
        ("<div><p> </p></div>", "<div></div>"),
        ("<div><p></p><span></span></div>", "<div></div>"),
        ("<div><p>Content</p><span></span></div>", "<div><p>Content</p></div>"),
        ("<div><p>Content</p><span> </span></div>", "<div><p>Content</p></div>"),
        (
            "<div><p>Content</p><span>Text</span></div>",
            "<div><p>Content</p><span>Text</span></div>",
        ),
    ],
)
def test_removes_empty_tags(html_content, expected_output):
    assert remove_empty_tags_from_html_content(html_content) == expected_output
