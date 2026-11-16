"""Keep streamed XML content and order while releasing consumed native tree nodes."""

import io

import pytest
from lxml import etree

from unstructured.partition.xml import _partition_events, get_leaf_elements


class ShortReads(io.BytesIO):
    def __init__(self, content, read_size):
        super().__init__(content)
        self.read_size = read_size

    def read(self, size=-1):
        return super().read(min(size, self.read_size) if size >= 0 else self.read_size)


@pytest.mark.parametrize("read_size", [1, 7, 32768])
@pytest.mark.parametrize(
    ("xml", "expected"),
    [
        ("<root><item>one</item><item>two</item></root>", ["one", "two"]),
        (
            "<root><record><a>A</a><b>B</b></record>BETWEEN"
            "<record><a>C</a><b>D</b></record>AFTER</root>",
            ["A", "B", "BETWEEN", "C", "D", "AFTER"],
        ),
        (
            "<root>prefix<b>bold</b><!-- note -->middle<?pi value?>end</root>",
            ["prefixboldmiddleend"],
        ),
        ("<root><!-- note --> <?pi value?> </root>", []),
        (
            "<root><wrapper><item>one</item></wrapper><item>two</item></root>",
            ["one", "two"],
        ),
        (
            '<root xmlns:n="urn:test"><n:item>café</n:item><n:item>茶</n:item></root>',
            ["café", "茶"],
        ),
        (
            "<root><outer> <inner>value</inner> </outer></root>",
            ["value"],
        ),
        (
            "<root><record><a>A</a><b>B</b></record><!-- note -->TAIL"
            "<?pi value?>END<record><a>C</a><b>D</b></record></root>",
            ["A", "B", "TAILEND", "C", "D"],
        ),
    ],
)
def test_streamed_xml_retains_content_across_native_node_cleanup(xml, expected, read_size):
    with ShortReads(xml.encode(), read_size) as stream:
        assert list(get_leaf_elements(None, stream, None, None)) == expected
        assert not stream.closed


def test_nonclearing_walk_preserves_the_tree_for_other_xpath_selections():
    root = etree.fromstring(
        "<root><record><a>A</a><b>B</b></record>TAIL"
        "<!-- note -->END<?pi value?><record><a>C</a><b>D</b></record></root>"
    )
    before = etree.tostring(root)

    values = list(
        _partition_events(
            etree.iterwalk(root, events=("start", "end", "comment", "pi")), clear=False
        )
    )

    assert values == ["A", "B", "TAILEND", "C", "D"]
    assert etree.tostring(root) == before
    assert len(root.xpath("./record")) == 2
