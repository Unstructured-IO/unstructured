import os
from collections.abc import Mapping
from html.parser import HTMLParser
from io import StringIO
from typing import Any, Callable, Hashable, Iterable, Iterator, Union

from huggingface_hub import hf_hub_download
from PIL import Image

from unstructured_inference.inference.layoutelement import LayoutElement


class LazyEvaluateInfo:
    """Class that stores the information needed to lazily evaluate a function with given arguments.
    The object stores the information needed for evaluation as a function and its arguments.
    """

    def __init__(self, evaluate: Callable, *args, **kwargs):
        self.evaluate = evaluate
        self.info = (args, kwargs)


class LazyDict(Mapping):
    """Class that wraps a dict and only evaluates keys of the dict when the key is accessed. Keys
    that should be evaluated lazily should use LazyEvaluateInfo objects as values. By default when
    a value is computed from a LazyEvaluateInfo object, it is converted to the raw value in the
    internal dict, so subsequent accessing of the key will produce the same value. Set cache=False
    to avoid storing the raw value.
    """

    def __init__(self, *args, cache=True, **kwargs):
        self.cache = cache
        self._raw_dict = dict(*args, **kwargs)

    def __getitem__(self, key: Hashable) -> Union[LazyEvaluateInfo, Any]:
        value = self._raw_dict.__getitem__(key)
        if isinstance(value, LazyEvaluateInfo):
            evaluate = value.evaluate
            args, kwargs = value.info
            value = evaluate(*args, **kwargs)
            if self.cache:
                self._raw_dict[key] = value
        return value

    def __iter__(self) -> Iterator:
        return iter(self._raw_dict)

    def __len__(self) -> int:
        return len(self._raw_dict)


def tag(elements: Iterable[LayoutElement]):
    """Asign an numeric id to the elements in the list.
    Useful for debugging"""
    colors = ["red", "blue", "green", "magenta", "brown"]
    for i, e in enumerate(elements):
        e.text = f"-{i}-:{e.text}"
        # currently not a property
        e.id = i  # type:ignore
        e.color = colors[i % len(colors)]  # type:ignore


def pad_image_with_background_color(
    image: Image.Image,
    pad: int = 10,
    background_color: str = "white",
) -> Image.Image:
    """pads an input image with the same background color around it by pad on all 4 sides

    The original image is kept intact and a new image is returned with padding added.
    """
    width, height = image.size
    if pad < 0:
        raise ValueError(
            "Can not pad an image with negative space! Please use a positive value for `pad`.",
        )
    new = Image.new(image.mode, (width + pad * 2, height + pad * 2), background_color)
    new.paste(image, (pad, pad))
    return new


class MLStripper(HTMLParser):
    """simple markup language stripper that helps to strip tags from string"""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = True
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        """process input data"""
        self.text.write(d)

    def get_data(self):
        """performs stripping by get the value of text"""
        return self.text.getvalue()


def strip_tags(html: str) -> str:
    """stripping html tags from input string and return string without tags"""
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def download_if_needed_and_get_local_path(path_or_repo: str, filename: str, **kwargs) -> str:
    """Returns path to local file if it exists, otherwise treats it as a huggingface repo and
    attempts to download."""
    full_path = os.path.join(path_or_repo, filename)
    if os.path.exists(full_path):
        return full_path
    else:
        return hf_hub_download(path_or_repo, filename, **kwargs)
