"""Tests for the regex constants in `unstructured.nlp.patterns`."""

import subprocess
import sys

import pytest

from unstructured.nlp.patterns import US_PHONE_NUMBERS_RE

SEPARATOR_CHARS = ["-", ".", " ", "(", ")"]

PAYLOAD_LENGTH = 2000

# The current pattern matches these payloads in under a millisecond, so this is orders of
# magnitude of headroom on a slow or loaded runner while still bounding a regression.
TIME_BUDGET_SECONDS = 5.0

_MATCH_SCRIPT = "import re, sys; re.search(sys.argv[1], sys.argv[2])"


def _search_completes_within(payload: str, timeout: float) -> bool:
    """Run the pattern against `payload` in a subprocess, bounded by `timeout`.

    CPython does not check for signals while a regex match is in progress, so an
    in-process alarm cannot interrupt one and a wall-clock assertion after the call
    cannot bound it. A separate process is what makes the budget enforceable.

    Args:
        payload (str): The text to match against.
        timeout (float): Seconds to allow before killing the subprocess.

    Returns:
        bool: True if the match completed within the timeout.
    """
    try:
        subprocess.run(
            [sys.executable, "-c", _MATCH_SCRIPT, US_PHONE_NUMBERS_RE.pattern, payload],
            timeout=timeout,
            capture_output=True,
            check=True,
        )
    except subprocess.TimeoutExpired:
        return False
    return True


@pytest.mark.parametrize("char", SEPARATOR_CHARS)
def test_us_phone_numbers_pattern_matches_long_separator_runs_within_budget(char: str):
    """A long run of separator characters must match in linear time.

    Such runs are common in extracted document text -- table borders, Markdown
    horizontal rules, email signature dividers.

    Args:
        char (str): A single character drawn from the pattern's separator classes.
    """
    assert _search_completes_within(char * PAYLOAD_LENGTH, TIME_BUDGET_SECONDS), (
        f"matching {PAYLOAD_LENGTH} {char!r} characters exceeded {TIME_BUDGET_SECONDS}s "
        f"-- the separator runs are likely unbounded again"
    )


def test_us_phone_numbers_pattern_matches_separator_run_with_digit_tail_within_budget():
    """A separator run followed by digits must also match in linear time."""
    payload = " " * PAYLOAD_LENGTH + "1234"

    assert _search_completes_within(payload, TIME_BUDGET_SECONDS), (
        f"matching a {PAYLOAD_LENGTH}-space run followed by digits exceeded "
        f"{TIME_BUDGET_SECONDS}s -- the separator runs are likely unbounded again"
    )


@pytest.mark.parametrize("char", SEPARATOR_CHARS)
def test_us_phone_numbers_pattern_does_not_read_separators_as_a_phone_number(char: str):
    """Separator-only text contains no phone number.

    Args:
        char (str): A single character drawn from the pattern's separator classes.
    """
    assert US_PHONE_NUMBERS_RE.search(char * 40) is None


@pytest.mark.parametrize(
    ("run_length", "is_matched"),
    [(0, True), (1, True), (2, True), (3, True), (4, False), (5, False), (10, False)],
)
def test_us_phone_numbers_pattern_bounds_the_run_between_final_digit_groups(
    run_length: int, is_matched: bool
):
    """Pin the bound at three characters where no adjacent class can absorb the overflow.

    Between the last two digit groups a single separator class applies, so this is the
    position that distinguishes `{0,3}` from a looser bound: a four-character run must
    not match.

    Args:
        run_length (int): Number of separator characters between the digit groups.
        is_matched (bool): Whether the pattern is expected to match.
    """
    text = "867" + ("-" * run_length) + "5309"

    assert (US_PHONE_NUMBERS_RE.search(text) is not None) is is_matched


@pytest.mark.parametrize(
    ("run_length", "is_full_match"),
    [(1, True), (2, True), (3, True), (4, False), (6, False), (10, False)],
)
def test_us_phone_numbers_pattern_bounds_the_run_before_the_prefix(
    run_length: int, is_full_match: bool
):
    """With no area code present, the runs either side of it cannot merge.

    The area code's trailing separator run is nested inside the optional area-code group,
    so when that group does not participate only the leading run applies. Without the
    nesting these two runs are adjacent and accept six characters between them.

    Args:
        run_length (int): Number of separator characters before the prefix.
        is_full_match (bool): Whether the whole string is expected to match.
    """
    text = "215" + ("-" * run_length) + "867-5309"

    match = US_PHONE_NUMBERS_RE.search(text)

    assert (match is not None and match.group() == text) is is_full_match


@pytest.mark.parametrize(
    ("run_length", "is_full_match"),
    [(0, True), (1, True), (3, True), (4, False), (5, False)],
)
def test_us_phone_numbers_pattern_bounds_the_run_after_the_area_code(
    run_length: int, is_full_match: bool
):
    """The area code's own trailing run is bounded when that group does participate.

    Covers the other separator branch: here the optional area-code group matches, so the
    run being bounded is the one nested inside it rather than the leading run.

    Args:
        run_length (int): Number of separator characters after the area code.
        is_full_match (bool): Whether the whole string is expected to match.
    """
    text = "1-800" + ("-" * run_length) + "867-5309"

    match = US_PHONE_NUMBERS_RE.search(text)

    assert (match is not None and match.group() == text) is is_full_match


@pytest.mark.parametrize("char", ["-", ".", " "])
def test_us_phone_numbers_pattern_does_not_absorb_long_separator_runs(char: str):
    """A separator run past the bound is excluded from the match rather than absorbed.

    Earlier in the string the leading digit group is dropped and a shorter trailing span
    matches instead, so the run itself never appears in full inside the result.

    Args:
        char (str): A separator character to repeat between the digit groups.
    """
    text = "215" + (char * 20) + "867-5309"

    match = US_PHONE_NUMBERS_RE.search(text)

    assert match is not None
    assert match.group() != text
    assert len(match.group()) < len(text)


@pytest.mark.parametrize(
    "text",
    [
        "215-867-5309",
        "+1 215.867.5309",
        "8675309",
        "2158675309",
        "+12158675309",
        "867.5309",
        "1-800-867-5309",
        "1(800)-867-5309",
        "(215) 867-5309",
        "215 . 867 . 5309",
        "Tel: 1(800)-867-5309",
        "Phone Number: 215-867-5309 x1234",
    ],
)
def test_us_phone_numbers_pattern_still_matches_real_numbers(text: str):
    """Bounding the separator runs must not narrow the set of accepted phone formats.

    Args:
        text (str): A string containing a US phone number in a supported format.
    """
    assert US_PHONE_NUMBERS_RE.search(text) is not None
