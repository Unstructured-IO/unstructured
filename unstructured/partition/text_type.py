"""partition.py implements logic for partitioning plain text documents into sections."""
import os
import re
import sys
from typing import List, Optional

if sys.version_info < (3, 8):
    from typing_extensions import Final  # pragma: nocover
else:
    from typing import Final

from unstructured.cleaners.core import remove_punctuation
from unstructured.logger import logger
from unstructured.nlp.english_words import ENGLISH_WORDS
from unstructured.nlp.patterns import (
    UNICODE_BULLETS_RE,
    US_CITY_STATE_ZIP_RE,
    US_PHONE_NUMBERS_RE,
)
from unstructured.nlp.tokenize import pos_tag, sent_tokenize, word_tokenize

POS_VERB_TAGS: Final[List[str]] = ["VB", "VBG", "VBD", "VBN", "VBP", "VBZ"]
ENGLISH_WORD_SPLIT_RE = re.compile(r"[\s|\.|-|_|\/]")


def is_possible_narrative_text(
    text: str,
    cap_threshold: float = 0.5,
    non_alpha_threshold: float = 0.5,
    language: str = "en",
    language_checks: bool = False,
) -> bool:
    """Checks to see if the text passes all of the checks for a narrative text section.
    You can change the cap threshold using the cap_threshold kwarg or the
    NARRATIVE_TEXT_CAP_THRESHOLD environment variable. The environment variable takes
    precedence over the kwarg.

    Parameters
    ----------
    text
        The input text to check
    cap_threshold
        The percentage of capitalized words necessary to disqualify the segment as narrative
    non_alpha_threshold
        The minimum proportion of alpha characters the text needs to be considered
        narrative text
    language
        The two letter language code for the text. defaults to "en" for English
    language_checks
        If True, conducts checks that are specific to the chosen language. Turn on for more
        accurate partitioning and off for faster processing.
    """
    _language_checks = os.environ.get("UNSTRUCTURED_LANGUAGE_CHECKS")
    if _language_checks is not None:
        language_checks = _language_checks.lower() == "true"

    if len(text) == 0:
        logger.debug("Not narrative. Text is empty.")
        return False

    if text.isnumeric():
        logger.debug(f"Not narrative. Text is all numeric:\n\n{text}")
        return False

    language = os.environ.get("UNSTRUCTURED_LANGUAGE", language)
    if language == "en" and language_checks and not contains_english_word(text):
        return False

    # NOTE(robinson): it gets read in from the environment as a string so we need to
    # cast it to a float
    cap_threshold = float(
        os.environ.get("UNSTRUCTURED_NARRATIVE_TEXT_CAP_THRESHOLD", cap_threshold),
    )
    if exceeds_cap_ratio(text, threshold=cap_threshold):
        logger.debug(f"Not narrative. Text exceeds cap ratio {cap_threshold}:\n\n{text}")
        return False

    non_alpha_threshold = float(
        os.environ.get("UNSTRUCTURED_NARRATIVE_TEXT_NON_ALPHA_THRESHOLD", non_alpha_threshold),
    )
    if under_non_alpha_ratio(text, threshold=non_alpha_threshold):
        return False

    if (sentence_count(text, 3) < 2) and (not contains_verb(text)) and language == "en":
        logger.debug(f"Not narrative. Text does not contain a verb:\n\n{text}")
        return False

    return True


def is_possible_title(
    text: str,
    sentence_min_length: int = 5,
    title_max_word_length: int = 12,
    non_alpha_threshold: float = 0.5,
    language: str = "en",
    language_checks: bool = False,
) -> bool:
    """Checks to see if the text passes all of the checks for a valid title.

    Parameters
    ----------
    text
        The input text to check
    sentence_min_length
        The minimum number of words required to consider a section of text a sentence
    title_max_word_length
        The maximum number of words a title can contain
    non_alpha_threshold
        The minimum number of alpha characters the text needs to be considered a title
    language
        The two letter language code for the text. defaults to "en" for English
    language_checks
        If True, conducts checks that are specific to the chosen language. Turn on for more
        accurate partitioning and off for faster processing.
    """
    _language_checks = os.environ.get("UNSTRUCTURED_LANGUAGE_CHECKS")
    if _language_checks is not None:
        language_checks = _language_checks.lower() == "true"

    if len(text) == 0:
        logger.debug("Not a title. Text is empty.")
        return False

    title_max_word_length = int(
        os.environ.get("UNSTRUCTURED_TITLE_MAX_WORD_LENGTH", title_max_word_length),
    )
    # NOTE(robinson) - splitting on spaces here instead of word tokenizing because it
    # is less expensive and actual tokenization doesn't add much value for the length check
    if len(text.split(" ")) > title_max_word_length:
        return False

    non_alpha_threshold = float(
        os.environ.get("UNSTRUCTURED_TITLE_NON_ALPHA_THRESHOLD", non_alpha_threshold),
    )
    if under_non_alpha_ratio(text, threshold=non_alpha_threshold):
        return False

    # NOTE(robinson) - Prevent flagging salutations like "To My Dearest Friends," as titles
    if text.endswith(","):
        return False

    language = os.environ.get("UNSTRUCTURED_LANGUAGE", language)
    if language == "en" and not contains_english_word(text) and language_checks:
        return False

    if text.isnumeric():
        logger.debug(f"Not a title. Text is all numeric:\n\n{text}")
        return False

    # NOTE(robinson) - The min length is to capture content such as "ITEM 1A. RISK FACTORS"
    # that sometimes get tokenized as separate sentences due to the period, but are still
    # valid titles
    if sentence_count(text, min_length=sentence_min_length) > 1:
        logger.debug(f"Not a title. Text is longer than {sentence_min_length} sentences:\n\n{text}")
        return False

    return True


def is_bulleted_text(text: str) -> bool:
    """Checks to see if the section of text is part of a bulleted list."""
    return UNICODE_BULLETS_RE.match(text.strip()) is not None


def contains_us_phone_number(text: str) -> bool:
    """Checks to see if a section of text contains a US phone number.

    Example
    -------
    contains_us_phone_number("867-5309") -> True
    """
    return US_PHONE_NUMBERS_RE.search(text.strip()) is not None


def contains_verb(text: str) -> bool:
    """Use a POS tagger to check if a segment contains verbs. If the section does not have verbs,
    that indicates that it is not narrative text."""
    if text.isupper():
        text = text.lower()

    pos_tags = pos_tag(text)
    return any(tag in POS_VERB_TAGS for _, tag in pos_tags)


def contains_english_word(text: str) -> bool:
    """Checks to see if the text contains an English word."""
    text = text.lower()
    words = ENGLISH_WORD_SPLIT_RE.split(text)
    for word in words:
        # NOTE(robinson) - to ignore punctuation at the ends of words like "best."
        word = "".join([character for character in word if character.isalpha()])
        if len(word) > 1 and word in ENGLISH_WORDS:
            return True

    return False


def sentence_count(text: str, min_length: Optional[int] = None) -> int:
    """Checks the sentence count for a section of text. Titles should not be more than one
    sentence.

    Parameters
    ----------
    text
        The string of the text to count
    min_length
        The min number of words a section needs to be for it to be considered a sentence.
    """
    sentences = sent_tokenize(text)
    count = 0
    for sentence in sentences:
        sentence = remove_punctuation(sentence)
        words = [word for word in word_tokenize(sentence) if word != "."]
        if min_length and len(words) < min_length:
            logger.debug(
                f"Skipping sentence because does not exceed {min_length} word tokens\n"
                f"{sentence}",
            )
            continue
        count += 1
    return count


def under_non_alpha_ratio(text: str, threshold: float = 0.5):
    """Checks if the proportion of non-alpha characters in the text snippet exceeds a given
    threshold. This helps prevent text like "-----------BREAK---------" from being tagged
    as a title or narrative text. The ratio does not count spaces.

    Parameters
    ----------
    text
        The input string to test
    threshold
        If the proportion of non-alpha characters exceeds this threshold, the function
        returns False
    """
    if len(text) == 0:
        return False

    alpha_count = len([char for char in text if char.strip() and char.isalpha()])
    total_count = len([char for char in text if char.strip()])
    ratio = alpha_count / total_count
    return ratio < threshold


def exceeds_cap_ratio(text: str, threshold: float = 0.5) -> bool:
    """Checks the title ratio in a section of text. If a sufficient proportion of the words
    are capitalized, that can be indicated on non-narrative text (i.e. "1A. Risk Factors").

    Parameters
    ----------
    text
        The input string to test
    threshold
        If the percentage of words beginning with a capital letter exceeds this threshold,
        the function returns True
    """
    # NOTE(robinson) - Currently limiting this to only sections of text with one sentence.
    # The assumption is that sections with multiple sentences are not titles.
    if sentence_count(text, 3) > 1:
        logger.debug(f"Text does not contain multiple sentences:\n\n{text}")
        return False

    if text.isupper():
        return False

    tokens = word_tokenize(text)
    if len(tokens) == 0:
        return False
    capitalized = sum([word.istitle() or word.isupper() for word in tokens])
    ratio = capitalized / len(tokens)
    return ratio > threshold


def is_us_city_state_zip(text) -> bool:
    """Checks if the given text is in the format of US city/state/zip code.

    Examples
    --------
    Doylestown, PA 18901
    Doylestown, Pennsylvania, 18901
    DOYLESTOWN, PENNSYLVANIA 18901
    """
    return US_CITY_STATE_ZIP_RE.match(text.strip()) is not None
