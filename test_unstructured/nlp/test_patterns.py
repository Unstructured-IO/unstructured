"""Tests for the regex constants in `unstructured.nlp.patterns`."""

import time

import pytest

from unstructured.nlp.patterns import US_PHONE_NUMBERS_RE

SEPARATOR_CHARS = ["-", ".", " ", "(", ")"]

# Sized so that a regression to unbounded separator runs is unambiguous while the test
# still finishes promptly: the current pattern matches this payload in ~0.3ms, the
# unbounded form took ~940ms. Keeping the payload small bounds how long a regressed
# pattern can occupy a test worker before the assertion is reached.
PAYLOAD_LENGTH = 800

# ~900x above the expected match time and ~4x below a regression, so the test is stable
# on a slow or loaded runner without losing its signal.
TIME_BUDGET_SECONDS = 0.25


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
        f"matching {PAYLOAD_LENGTH} {char!r} characters took {elapsed:.3f}s "
        f"(budget {TIME_BUDGET_SECONDS}s) -- the separator runs are likely unbounded again"
    )


def test_us_phone_numbers_pattern_matches_separator_run_with_digit_tail_quickly():
    """A separator run followed by digits must also match in linear time."""
    payload = " " * PAYLOAD_LENGTH + "1234"

    start = time.perf_counter()
    US_PHONE_NUMBERS_RE.search(payload)
    elapsed = time.perf_counter() - start

    assert elapsed < TIME_BUDGET_SECONDS, (
        f"matching a {PAYLOAD_LENGTH}-space run followed by digits took {elapsed:.3f}s "
        f"(budget {TIME_BUDGET_SECONDS}s) -- the separator runs are likely unbounded again"
    )


@pytest.mark.parametrize("char", ["-", ".", " "])
def test_us_phone_numbers_pattern_does_not_absorb_long_separator_runs(char: str):
    """A separator run past the bound is excluded from the match rather than absorbed.

    The leading digit group is dropped and a shorter trailing span matches instead, so
    the run itself never appears in full inside the result.

    Args:
        char (str): A separator character to repeat between the digit groups.
    """
    text = "215" + (char * 20) + "867-5309"

    match = US_PHONE_NUMBERS_RE.search(text)

    assert match is not None
    assert match.group() != text
    assert len(match.group()) < len(text)


def test_us_phone_numbers_pattern_rejects_long_run_between_final_digit_groups():
    """A run past the bound between the last two digit groups leaves nothing to match.

    Unlike a run earlier in the string, there is no shorter trailing span that satisfies
    the pattern, so the input is not matched at all.
    """
    assert US_PHONE_NUMBERS_RE.search("867" + ("-" * 10) + "5309") is None


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
