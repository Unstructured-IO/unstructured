import numpy as np
import pytest

from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.utils import (
    LazyDict,
    LazyEvaluateInfo,
    pad_image_with_background_color,
    strip_tags,
)


# Mocking the DocumentLayout and Page classes
class MockPageLayout:
    def annotate(self, annotation_data):
        return "mock_image"


class MockDocumentLayout(DocumentLayout):
    @property
    def pages(self):
        return [MockPageLayout(), MockPageLayout()]


def test_dict_same():
    d = {"a": 1, "b": 2, "c": 3}
    ld = LazyDict(**d)
    assert all(kd == kld for kd, kld in zip(d, ld))
    assert all(d[k] == ld[k] for k in d)
    assert len(ld) == len(d)


def test_lazy_evaluate():
    called = 0

    def func(x):
        nonlocal called
        called += 1
        return x

    lei = LazyEvaluateInfo(func, 3)
    assert called == 0
    ld = LazyDict(a=lei)
    assert called == 0
    assert ld["a"] == 3
    assert called == 1


@pytest.mark.parametrize(("cache", "expected"), [(True, 1), (False, 2)])
def test_caches(cache, expected):
    called = 0

    def func(x):
        nonlocal called
        called += 1
        return x

    lei = LazyEvaluateInfo(func, 3)
    assert called == 0
    ld = LazyDict(cache=cache, a=lei)
    assert called == 0
    assert ld["a"] == 3
    assert ld["a"] == 3
    assert called == expected


def test_pad_image_with_background_color(mock_pil_image):
    pad = 10
    height, width = mock_pil_image.size
    padded = pad_image_with_background_color(mock_pil_image, pad, "black")
    assert padded.size == (height + 2 * pad, width + 2 * pad)
    np.testing.assert_array_almost_equal(
        np.array(padded.crop((pad, pad, width + pad, height + pad))),
        np.array(mock_pil_image),
    )
    assert padded.getpixel((1, 1)) == (0, 0, 0)


def test_pad_image_with_invalid_input(mock_pil_image):
    with pytest.raises(ValueError, match="Can not pad an image with negative space!"):
        pad_image_with_background_color(mock_pil_image, -1)


@pytest.mark.parametrize(
    ("html", "text"),
    [
        ("<table>Table</table>", "Table"),
        # test escaped character
        ("<table>y&ltx, x&gtz</table>", "y<x, x>z"),
        # test tag with parameters
        ("<table format=foo>Table", "Table"),
    ],
)
def test_strip_tags(html, text):
    assert strip_tags(html) == text
