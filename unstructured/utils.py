from __future__ import annotations

import asyncio
import functools
import html
import importlib
import inspect
import json
import os
import platform
import subprocess
import tempfile
import threading
from datetime import datetime
from functools import wraps
from itertools import combinations
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)

import requests
from typing_extensions import ParamSpec, TypeAlias

from unstructured.__version__ import __version__

if TYPE_CHECKING:
    from unstructured.documents.elements import Element, Text

# Box format: [x_bottom_left, y_bottom_left, x_top_right, y_top_right]
Box: TypeAlias = Tuple[float, float, float, float]
Point: TypeAlias = Tuple[float, float]
Points: TypeAlias = Tuple[Point, ...]

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d+%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")

_T = TypeVar("_T")
_P = ParamSpec("_P")


def get_call_args_applying_defaults(
    func: Callable[_P, List[Element]],
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> dict[str, Any]:
    """Map both explicit and default arguments of decorated func call by param name."""
    sig = inspect.signature(func)
    call_args: dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
    for arg in sig.parameters.values():
        if arg.name not in call_args and arg.default is not arg.empty:
            call_args[arg.name] = arg.default
    return call_args


def htmlify_matrix_of_cell_texts(matrix: Sequence[Sequence[str]]) -> str:
    """Form an HTML table from "rows" and "columns" of `matrix`.

    Character overhead is minimized:
    - No whitespace padding is added for human readability
    - No newlines ("\n") are added
    - No `<thead>`, `<tbody>`, or `<tfoot>` elements are used; we can't tell where those might be
      semantically appropriate anyway so at best they would consume unnecessary space and at worst
      would be misleading.
    """

    def iter_trs(rows_of_cell_strs: Sequence[Sequence[str]]) -> Iterator[str]:
        for row_cell_strs in rows_of_cell_strs:
            # -- suppress emission of rows with no cells --
            if not row_cell_strs:
                continue
            yield f"<tr>{''.join(iter_tds(row_cell_strs))}</tr>"

    def iter_tds(row_cell_strs: Sequence[str]) -> Iterator[str]:
        for s in row_cell_strs:
            # -- take care of things like '<' and '>' in the text --
            s = html.escape(s)
            # -- substitute <br/> elements for line-feeds in the text --
            s = "<br/>".join(s.split("\n"))
            # -- strip leading and trailing whitespace, wrap it up and go --
            yield f"<td>{s.strip()}</td>"

    return f"<table>{''.join(iter_trs(matrix))}</table>" if matrix else ""


def is_temp_file_path(file_path: str) -> bool:
    """True when file_path is in the Python-defined tempdir.

    The Python-defined temp directory is platform dependent (macOS != Linux != Windows)
    and can also be determined by an environment variable (TMPDIR, TEMP, or TMP).
    """
    return file_path.startswith(tempfile.gettempdir())


class lazyproperty(Generic[_T]):
    """Decorator like @property, but evaluated only on first access.

    Like @property, this can only be used to decorate methods having only a `self` parameter, and
    is accessed like an attribute on an instance, i.e. trailing parentheses are not used. Unlike
    @property, the decorated method is only evaluated on first access; the resulting value is
    cached and that same value returned on second and later access without re-evaluation of the
    method.

    Like @property, this class produces a *data descriptor* object, which is stored in the __dict__
    of the *class* under the name of the decorated method ('fget' nominally). The cached value is
    stored in the __dict__ of the *instance* under that same name.

    Because it is a data descriptor (as opposed to a *non-data descriptor*), its `__get__()` method
    is executed on each access of the decorated attribute; the __dict__ item of the same name is
    "shadowed" by the descriptor.

    While this may represent a performance improvement over a property, its greater benefit may be
    its other characteristics. One common use is to construct collaborator objects, removing that
    "real work" from the constructor, while still only executing once. It also de-couples client
    code from any sequencing considerations; if it's accessed from more than one location, it's
    assured it will be ready whenever needed.

    Loosely based on: https://stackoverflow.com/a/6849299/1902513.

    A lazyproperty is read-only. There is no counterpart to the optional "setter" (or deleter)
    behavior of an @property. This is critically important to maintaining its immutability and
    idempotence guarantees. Attempting to assign to a lazyproperty raises AttributeError
    unconditionally.

    The parameter names in the methods below correspond to this usage example::

        class Obj(object)

            @lazyproperty
            def fget(self):
                return 'some result'

        obj = Obj()

    Not suitable for wrapping a function (as opposed to a method) because it is not callable.
    """

    def __init__(self, fget: Callable[..., _T]) -> None:
        """*fget* is the decorated method (a "getter" function).

        A lazyproperty is read-only, so there is only an *fget* function (a regular
        @property can also have an fset and fdel function). This name was chosen for
        consistency with Python's `property` class which uses this name for the
        corresponding parameter.
        """
        # --- maintain a reference to the wrapped getter method
        self._fget = fget
        # --- and store the name of that decorated method
        self._name = fget.__name__
        # --- adopt fget's __name__, __doc__, and other attributes
        functools.update_wrapper(self, fget)  # pyright: ignore

    def __get__(self, obj: Any, type: Any = None) -> _T:
        """Called on each access of 'fget' attribute on class or instance.

        *self* is this instance of a lazyproperty descriptor "wrapping" the property
        method it decorates (`fget`, nominally).

        *obj* is the "host" object instance when the attribute is accessed from an
        object instance, e.g. `obj = Obj(); obj.fget`. *obj* is None when accessed on
        the class, e.g. `Obj.fget`.

        *type* is the class hosting the decorated getter method (`fget`) on both class
        and instance attribute access.
        """
        # --- when accessed on class, e.g. Obj.fget, just return this descriptor
        # --- instance (patched above to look like fget).
        if obj is None:
            return self  # type: ignore

        # --- when accessed on instance, start by checking instance __dict__ for
        # --- item with key matching the wrapped function's name
        value = obj.__dict__.get(self._name)
        if value is None:
            # --- on first access, the __dict__ item will be absent. Evaluate fget()
            # --- and store that value in the (otherwise unused) host-object
            # --- __dict__ value of same name ('fget' nominally)
            value = self._fget(obj)
            obj.__dict__[self._name] = value
        return cast(_T, value)

    def __set__(self, obj: Any, value: Any) -> None:
        """Raises unconditionally, to preserve read-only behavior.

        This decorator is intended to implement immutable (and idempotent) object
        attributes. For that reason, assignment to this property must be explicitly
        prevented.

        If this __set__ method was not present, this descriptor would become a
        *non-data descriptor*. That would be nice because the cached value would be
        accessed directly once set (__dict__ attrs have precedence over non-data
        descriptors on instance attribute lookup). The problem is, there would be
        nothing to stop assignment to the cached value, which would overwrite the result
        of `fget()` and break both the immutability and idempotence guarantees of this
        decorator.

        The performance with this __set__() method in place was roughly 0.4 usec per
        access when measured on a 2.8GHz development machine; so quite snappy and
        probably not a rich target for optimization efforts.
        """
        raise AttributeError("can't set attribute")


def save_as_jsonl(data: list[dict[str, Any]], filename: str) -> None:
    with open(filename, "w+") as output_file:
        output_file.writelines(json.dumps(datum) + "\n" for datum in data)


def read_from_jsonl(filename: str) -> list[dict[str, Any]]:
    with open(filename) as input_file:
        return [json.loads(line) for line in input_file]


def requires_dependencies(
    dependencies: str | list[str],
    extras: Optional[str] = None,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    if isinstance(dependencies, str):
        dependencies = [dependencies]

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        def run_check():
            missing_deps: List[str] = []
            for dep in dependencies:
                if not dependency_exists(dep):
                    missing_deps.append(dep)
            if len(missing_deps) > 0:
                raise ImportError(
                    f"Following dependencies are missing: {', '.join(missing_deps)}. "
                    + (
                        f"""Please install them using `pip install "unstructured[{extras}]"`."""
                        if extras
                        else f"Please install them using `pip install {' '.join(missing_deps)}`."
                    ),
                )

        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            run_check()
            return func(*args, **kwargs)

        @wraps(func)
        async def wrapper_async(*args: _P.args, **kwargs: _P.kwargs):
            run_check()
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        return wrapper

    return decorator


def dependency_exists(dependency: str):
    try:
        importlib.import_module(dependency)
    except ImportError as e:
        # Check to make sure this isn't some unrelated import error.
        if dependency in repr(e):
            return False
    return True


def validate_date_args(date: Optional[str] = None) -> bool:
    """Validate whether the provided date string satisfies any of the supported date formats.

    Used by unstructured/ingest/connector/biomed.py

    Returns `True` if the date string satisfies any of the supported formats, otherwise raises
    `ValueError`.

    Supported Date Formats:
        - 'YYYY-MM-DD'
        - 'YYYY-MM-DDTHH:MM:SS'
        - 'YYYY-MM-DD+HH:MM:SS'
        - 'YYYY-MM-DDTHH:MM:SS±HHMM'
    """
    if not date:
        raise ValueError("The argument date is None.")

    for format in DATE_FORMATS:
        try:
            datetime.strptime(date, format)
            return True
        except ValueError:
            pass

    raise ValueError(
        f"The argument {date} does not satisfy the format:"
        f" YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SS±HHMM",
    )


def _first_and_remaining_iterator(it: Iterable[_T]) -> Tuple[_T, Iterator[_T]]:
    iterator = iter(it)
    try:
        out = next(iterator)
    except StopIteration:
        raise ValueError(
            "Expected at least 1 element in iterable from which to retrieve first, got empty "
            "iterable.",
        )
    return out, iterator


def first(it: Iterable[_T]) -> _T:
    """Returns the first item from an iterable. Raises an error if the iterable is empty."""
    out, _ = _first_and_remaining_iterator(it)
    return out


def only(it: Iterable[Any]) -> Any:
    """Returns the only element from a singleton iterable.

    Raises an error if the iterable is not a singleton.
    """
    out, iterator = _first_and_remaining_iterator(it)
    if any(True for _ in iterator):
        raise ValueError(
            "Expected only 1 element in passed argument, instead there are at least 2 elements.",
        )
    return out


def scarf_analytics():
    try:
        subprocess.check_output("nvidia-smi")
        gpu_present = True
    except Exception:
        gpu_present = False

    python_version = ".".join(platform.python_version().split(".")[:2])

    try:
        if os.getenv("SCARF_NO_ANALYTICS") != "true" and os.getenv("DO_NOT_TRACK") != "true":
            if "dev" in __version__:
                requests.get(
                    "https://packages.unstructured.io/python-telemetry?version="
                    + __version__
                    + "&platform="
                    + platform.system()
                    + "&python"
                    + python_version
                    + "&arch="
                    + platform.machine()
                    + "&gpu="
                    + str(gpu_present)
                    + "&dev=true",
                )
            else:
                requests.get(
                    "https://packages.unstructured.io/python-telemetry?version="
                    + __version__
                    + "&platform="
                    + platform.system()
                    + "&python"
                    + python_version
                    + "&arch="
                    + platform.machine()
                    + "&gpu="
                    + str(gpu_present)
                    + "&dev=false",
                )
    except Exception:
        pass


def ngrams(s: list[str], n: int) -> list[tuple[str, ...]]:
    """Generate n-grams from a list of strings where `n` (int) is the size of each n-gram."""

    ngrams_list: list[tuple[str, ...]] = []
    for i in range(len(s) - n + 1):
        ngram: list[str] = []
        for j in range(n):
            ngram.append(s[i + j])
        ngrams_list.append(tuple(ngram))
    return ngrams_list


def calculate_shared_ngram_percentage(
    first_string: str,
    second_string: str,
    n: int,
) -> tuple[float, set[tuple[str, ...]]]:
    """Calculate the percentage of common_ngrams between string A and B with reference to A"""
    if not n:
        return 0, set()
    first_string_ngrams = ngrams(first_string.split(), n)
    second_string_ngrams = ngrams(second_string.split(), n)

    if not first_string_ngrams:
        return 0, set()

    common_ngrams = set(first_string_ngrams) & set(second_string_ngrams)
    percentage = (len(common_ngrams) / len(first_string_ngrams)) * 100
    return percentage, common_ngrams


def calculate_largest_ngram_percentage(
    first_string: str, second_string: str
) -> tuple[float, set[tuple[str, ...]], str]:
    """From two strings, calculate the shared ngram percentage.

    Returns a tuple containing...
        - The largest n-gram percentage shared between the two strings.
        - A set containing the shared n-grams found during the calculation.
        - A string representation of the size of the largest shared n-grams found.
    """
    shared_ngrams: set[tuple[str, ...]] = set()
    if len(first_string.split()) < len(second_string.split()):
        n = len(first_string.split()) - 1
    else:
        n = len(second_string.split()) - 1
        first_string, second_string = second_string, first_string
    ngram_percentage = 0
    # Start from the biggest ngram possible (`n`) until the ngram_percentage is >0.0% or n == 0
    while not ngram_percentage:
        ngram_percentage, shared_ngrams = calculate_shared_ngram_percentage(
            first_string,
            second_string,
            n,
        )
        if n == 0:
            break
        else:
            n -= 1
    return round(ngram_percentage, 2), shared_ngrams, str(n + 1)


def is_parent_box(parent_target: Box, child_target: Box, add: float = 0.0) -> bool:
    """True if the child_target bounding box is nested in the parent_target.

    Box format: [x_bottom_left, y_bottom_left, x_top_right, y_top_right].
    The parameter 'add' is the pixel error tolerance for extra pixels outside the parent region
    """
    if len(parent_target) != 4:
        return False
    parent_targets = [0, 0, 0, 0]
    if add and len(parent_target) == 4:
        parent_targets = list(parent_target)
        parent_targets[0] -= add
        parent_targets[1] -= add
        parent_targets[2] += add
        parent_targets[3] += add

    if (
        len(child_target) == 4
        and (child_target[0] >= parent_targets[0] and child_target[1] >= parent_targets[1])
        and (child_target[2] <= parent_targets[2] and child_target[3] <= parent_targets[3])
    ):
        return True
    if len(child_target) == 2 and (
        parent_targets[0] <= child_target[0] <= parent_targets[2]
        and parent_targets[1] <= child_target[1] <= parent_targets[3]
    ):
        return True
    return False


def calculate_overlap_percentage(
    box1: Points,
    box2: Points,
    intersection_ratio_method: str = "total",
) -> tuple[float, float, float, float]:
    """Calculate the percentage of overlapped region.

    Calculate the percentage with reference to
    the biggest element-region (intersection_ratio_method="parent"),
    the smallest element-region (intersection_ratio_method="partial"), or
    the disjunctive union region (intersection_ratio_method="total")
    """
    x1, y1 = box1[0]
    x2, y2 = box1[2]
    x3, y3 = box2[0]
    x4, y4 = box2[2]
    area_box1 = (x2 - x1) * (y2 - y1)
    area_box2 = (x4 - x3) * (y4 - y3)
    x_intersection1 = max(x1, x3)
    y_intersection1 = max(y1, y3)
    x_intersection2 = min(x2, x4)
    y_intersection2 = min(y2, y4)
    intersection_area = max(0, x_intersection2 - x_intersection1) * max(
        0,
        y_intersection2 - y_intersection1,
    )
    max_area = max(area_box1, area_box2)
    min_area = min(area_box1, area_box2)
    total_area = area_box1 + area_box2

    if intersection_ratio_method == "parent":
        if max_area == 0:
            return 0, 0, 0, 0
        overlap_percentage = (intersection_area / max_area) * 100

    elif intersection_ratio_method == "partial":
        if min_area == 0:
            return 0, 0, 0, 0
        overlap_percentage = (intersection_area / min_area) * 100

    else:
        if (area_box1 + area_box2) == 0:
            return 0, 0, 0, 0

        overlap_percentage = (intersection_area / (area_box1 + area_box2 - intersection_area)) * 100

    return round(overlap_percentage, 2), max_area, min_area, total_area


def identify_overlapping_case(
    box_pair: list[Points] | tuple[Points, Points],
    label_pair: list[str] | tuple[str, str],
    text_pair: list[str] | tuple[str, str],
    ix_pair: list[str] | tuple[str, str],
    sm_overlap_threshold: float = 10.0,
):
    """Classifies the overlapping case for an element_pair input.

    There are 5 cases of overlapping:
        'Small partial overlap'
        'Partial overlap with empty content'
        'Partial overlap with duplicate text (sharing 100% of the text)'
        'Partial overlap without sharing text'
        'Partial overlap sharing {calculate_largest_ngram_percentage(...)}% of the text'

    Returns:
    overlapping_elements: List[str] - List of element types with their `ix` value.
        Ex: ['Title(ix=0)']
    overlapping_case: str - See list of cases above
    overlap_percentage: float
    largest_ngram_percentage: float
    max_area: float
    min_area: float
    total_area: float
    """
    overlapping_elements, overlapping_case, overlap_percentage, largest_ngram_percentage = (
        None,
        None,
        None,
        None,
    )
    box1, box2 = box_pair
    type1, type2 = label_pair
    text1, text2 = text_pair
    ix_element1, ix_element2 = ix_pair
    (overlap_percentage, max_area, min_area, total_area) = calculate_overlap_percentage(
        box1,
        box2,
        intersection_ratio_method="partial",
    )
    if overlap_percentage < sm_overlap_threshold:
        overlapping_elements = [
            f"{type1}(ix={ix_element1})",
            f"{type2}(ix={ix_element2})",
        ]
        overlapping_case = "Small partial overlap"

    else:
        if not text1:
            overlapping_elements = [
                f"{type1}(ix={ix_element1})",
                f"{type2}(ix={ix_element2})",
            ]
            overlapping_case = f"partial overlap with empty content in {type1}"

        elif not text2:
            overlapping_elements = [
                f"{type2}(ix={ix_element2})",
                f"{type1}(ix={ix_element1})",
            ]
            overlapping_case = f"partial overlap with empty content in {type2}"

        elif text1 in text2 or text2 in text1:
            overlapping_elements = [
                f"{type1}(ix={ix_element1})",
                f"{type2}(ix={ix_element2})",
            ]
            overlapping_case = "partial overlap with duplicate text"

        else:
            largest_ngram_percentage, _, largest_n = calculate_largest_ngram_percentage(
                text1, text2
            )
            largest_ngram_percentage = round(largest_ngram_percentage, 2)
            if not largest_ngram_percentage:
                overlapping_elements = [
                    f"{type1}(ix={ix_element1})",
                    f"{type2}(ix={ix_element2})",
                ]
                overlapping_case = "partial overlap without sharing text"

            else:
                overlapping_elements = [
                    f"{type1}(ix={ix_element1})",
                    f"{type2}(ix={ix_element2})",
                ]
                ref_type = type1 if len(text1.split()) < len(text2.split()) else type2
                ref_type = "of the text from" + ref_type + f"({largest_n}-gram)"
                overlapping_case = f"partial overlap sharing {largest_ngram_percentage}% {ref_type}"
    return (
        overlapping_elements,
        overlapping_case,
        overlap_percentage,
        largest_ngram_percentage,
        max_area,
        min_area,
        total_area,
    )


def _convert_coordinates_to_box(coordinates: Points):
    """Accepts a set of Points and returns the lower-left and upper-right coordinates.

    Expects four coordinates representing the corners of a rectangle, listed in this order:
    bottom-left, top-left, top-right, bottom-right.
    """
    x_bottom_left_1, y_bottom_left_1 = coordinates[0]
    x_top_right_1, y_top_right_1 = coordinates[2]
    return x_bottom_left_1, y_bottom_left_1, x_top_right_1, y_top_right_1


# x1, y1 = box1[0]
def identify_overlapping_or_nesting_case(
    box_pair: list[Points] | tuple[Points, Points],
    label_pair: list[str] | tuple[str, str],
    text_pair: list[str] | tuple[str, str],
    nested_error_tolerance_px: int = 5,
    sm_overlap_threshold: float = 10.0,
):
    """Identify if overlapping or nesting elements exist and, if so, the type of overlapping case.

    Returns:
    overlapping_elements: List[str] - List of element types & their `ix` value. Ex: ['Title(ix=0)']
    overlapping_case: str - See list of cases above
    overlap_percentage: float
    overlap_percentage_total: float
    largest_ngram_percentage: float
    max_area: float
    min_area: float
    total_area: float
    """
    box1, box2 = box_pair
    type1, type2 = label_pair
    ix_element1 = "".join([ch for ch in type1 if ch.isnumeric()])
    ix_element2 = "".join([ch for ch in type2 if ch.isnumeric()])
    type1 = type1[3:].strip()
    type2 = type2[3:].strip()
    box1_corners = _convert_coordinates_to_box(box1)
    box2_corners = _convert_coordinates_to_box(box2)
    x_bottom_left_1, y_bottom_left_1, x_top_right_1, y_top_right_1 = box1_corners
    x_bottom_left_2, y_bottom_left_2, x_top_right_2, y_top_right_2 = box2_corners

    horizontal_overlap = x_bottom_left_1 < x_top_right_2 and x_top_right_1 > x_bottom_left_2
    vertical_overlap = y_bottom_left_1 < y_top_right_2 and y_top_right_1 > y_bottom_left_2
    (
        overlapping_elements,
        parent_element,
        overlapping_case,
        overlap_percentage,
        overlap_percentage_total,
        largest_ngram_percentage,
    ) = (
        None,
        None,
        None,
        None,
        None,
        None,
    )
    max_area, min_area, total_area = None, None, None

    if horizontal_overlap and vertical_overlap:
        overlap_percentage_total, _, _, _ = calculate_overlap_percentage(
            box1,
            box2,
            intersection_ratio_method="total",
        )
        overlap_percentage, max_area, min_area, total_area = calculate_overlap_percentage(
            box1,
            box2,
            intersection_ratio_method="parent",
        )

        if is_parent_box(box1_corners, box2_corners, add=nested_error_tolerance_px):
            overlapping_elements = [
                f"{type1}(ix={ix_element1})",
                f"{type2}(ix={ix_element2})",
            ]
            overlapping_case = f"nested {type2} in {type1}"
            overlap_percentage = 100
            parent_element = f"{type1}(ix={ix_element1})"

        elif is_parent_box(box2_corners, box1_corners, add=nested_error_tolerance_px):
            overlapping_elements = [
                f"{type2}(ix={ix_element2})",
                f"{type1}(ix={ix_element1})",
            ]
            overlapping_case = f"nested {type1} in {type2}"
            overlap_percentage = 100
            parent_element = f"{type2}(ix={ix_element2})"

        else:
            (
                overlapping_elements,
                overlapping_case,
                overlap_percentage,
                largest_ngram_percentage,
                max_area,
                min_area,
                total_area,
            ) = identify_overlapping_case(
                box_pair,
                label_pair,
                text_pair,
                (ix_element1, ix_element2),
                sm_overlap_threshold=sm_overlap_threshold,
            )
    return (
        overlapping_elements,
        parent_element,
        overlapping_case,
        overlap_percentage or 0,
        overlap_percentage_total or 0,
        largest_ngram_percentage or 0,
        max_area or 0,
        min_area or 0,
        total_area or 0,
    )


def catch_overlapping_and_nested_bboxes(
    elements: list["Text"],
    nested_error_tolerance_px: int = 5,
    sm_overlap_threshold: float = 10.0,
) -> tuple[bool, list[dict[str, Any]]]:
    """Catch overlapping and nested bounding boxes cases across a list of elements."""

    num_pages = elements[-1].metadata.page_number or 0
    pages_of_bboxes: list[list[Points]] = [[] for _ in range(num_pages)]

    text_labels: list[list[str]] = [[] for _ in range(num_pages)]
    text_content: list[list[str]] = [[] for _ in range(num_pages)]

    for ix, element in enumerate(elements):
        page_number = element.metadata.page_number or 1
        n_page_to_ix = page_number - 1
        if element.metadata.coordinates:
            box = cast(Points, element.metadata.coordinates.to_dict()["points"])
            pages_of_bboxes[n_page_to_ix].append(box)
        text_labels[n_page_to_ix].append(f"{ix}. {element.category}")
        text_content[n_page_to_ix].append(element.text)

    document_with_overlapping_flag = False
    overlapping_cases: list[dict[str, Any]] = []
    for page_number, (page_bboxes, page_labels, page_text) in enumerate(
        zip(pages_of_bboxes, text_labels, text_content),
        start=1,
    ):
        page_bboxes_combinations = list(combinations(page_bboxes, 2))
        page_labels_combinations = list(combinations(page_labels, 2))
        text_content_combinations = list(combinations(page_text, 2))

        for box_pair, label_pair, text_pair in zip(
            page_bboxes_combinations,
            page_labels_combinations,
            text_content_combinations,
        ):
            (
                overlapping_elements,
                parent_element,
                overlapping_case,
                overlap_percentage,
                overlap_percentage_total,
                largest_ngram_percentage,
                max_area,
                min_area,
                total_area,
            ) = identify_overlapping_or_nesting_case(
                box_pair,
                label_pair,
                text_pair,
                nested_error_tolerance_px,
                sm_overlap_threshold,
            )

            if overlapping_case:
                overlapping_cases.append(
                    {
                        "overlapping_elements": overlapping_elements,
                        "parent_element": parent_element,
                        "overlapping_case": overlapping_case,
                        "overlap_percentage": f"{overlap_percentage}%",
                        "metadata": {
                            "largest_ngram_percentage": largest_ngram_percentage,
                            "overlap_percentage_total": f"{overlap_percentage_total}%",
                            "max_area": f"{round(max_area, 2)}pxˆ2",
                            "min_area": f"{round(min_area, 2)}pxˆ2",
                            "total_area": f"{round(total_area, 2)}pxˆ2",
                        },
                    },
                )
                document_with_overlapping_flag = True

    return document_with_overlapping_flag, overlapping_cases


class FileHandler:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lock = threading.Lock()

    def read_file(self):
        with self.lock:
            with open(self.file_path) as file:
                data = file.read()
            return data

    def write_file(self, data: str) -> None:
        with self.lock:
            with open(self.file_path, "w") as file:
                file.write(data)

    def cleanup_file(self):
        with self.lock:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
