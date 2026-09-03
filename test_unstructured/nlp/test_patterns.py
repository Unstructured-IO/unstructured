"""Tests for the regex constants in `unstructured.nlp.patterns`."""

import time

import pytest

from unstructured.nlp.patterns import US_PHONE_NUMBERS_RE

SEPARATOR_CHARS = ["-", ".", " ", "(", ")"]

PAYLOAD_LENGTH = 2000

# Generous relative to the expected sub-millisecond match time, so the test stays stable
# on a slow or loaded CI runner.
TIME_BUDGET_SECONDS = 2.0


@pytest.mark.parametrize("char", SEPARATOR_CHARS)
def test_us_phone_numbers_pattern_matches_long_separator_runs_quickly(char: str):
    """A long run of separator characters must match in linear time.

    Such runs are common in extracted document text -- table borders, Markdown
    horizontal rules, email signature dividers.

    Args:
        char (str): A single character drawn from the pattern's separator classes.
    """
    payload = char * PAYLOAD_LENGTH

    start = time.perf_counter()
    match = US_PHONE_NUMBERS_RE.search(payload)
    elapsed = time.perf_counter() - start

    assert match is None, "separator-only input should not be read as a phone number"
    assert elapsed < TIME_BUDGET_SECONDS, (
        f"matching {PAYLOAD_LENGTH} {char!r} characters took {elapsed:.2f}s "
        f"(budget {TIME_BUDGET_SECONDS}s) -- the separator runs are likely unbounded again"
    )


def test_us_phone_numbers_pattern_matches_separator_run_with_digit_tail_quickly():
    """A separator run followed by digits must also match in linear time."""
    payload = " " * PAYLOAD_LENGTH + "1234"

    start = time.perf_counter()
    US_PHONE_NUMBERS_RE.search(payload)
    elapsed = time.perf_counter() - start

    assert elapsed < TIME_BUDGET_SECONDS, (
        f"matching a {PAYLOAD_LENGTH}-space run followed by digits took {elapsed:.2f}s "
        f"(budget {TIME_BUDGET_SECONDS}s) -- the separator runs are likely unbounded again"
    )


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
