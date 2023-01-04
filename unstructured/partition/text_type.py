"""partition.py implements logic for partitioning plain text documents into sections."""
import sys

from typing import List, Optional

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from unstructured.cleaners.core import remove_punctuation
from unstructured.nlp.patterns import US_PHONE_NUMBERS_RE, UNICODE_BULLETS_RE
from unstructured.nlp.tokenize import pos_tag, sent_tokenize, word_tokenize
from unstructured.logger import logger


POS_VERB_TAGS: Final[List[str]] = ["VB", "VBG", "VBD", "VBN", "VBP", "VBZ"]


def is_possible_narrative_text(text: str, cap_threshold: float = 0.3) -> bool:
    """Checks to see if the text passes all of the checks for a narrative text section."""
    if len(text) == 0:
        logger.debug("Not narrative. Text is empty.")
        return False

    if text.isnumeric():
        logger.debug(f"Not narrative. Text is all numeric:\n\n{text}")
        return False

    if exceeds_cap_ratio(text, threshold=cap_threshold):
        logger.debug(f"Not narrative. Text exceeds cap ratio {cap_threshold}:\n\n{text}")
        return False

    if (sentence_count(text, 3) < 2) and (not contains_verb(text)):
        logger.debug(f"Not narrative. Text does not contain a verb:\n\n{text}")
        return False

    return True


def is_possible_title(text: str, sentence_min_length: int = 5) -> bool:
    """Checks to see if the text passes all of the checks for a valid title."""
    if len(text) == 0:
        logger.debug("Not a title. Text is empty.")
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
    pos_tags = pos_tag(text)
    for _, tag in pos_tags:
        if tag in POS_VERB_TAGS:
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
                f"{sentence}"
            )
            continue
        count += 1
    return count


def exceeds_cap_ratio(text: str, threshold: float = 0.3) -> bool:
    """Checks the title ratio in a section of text. If a sufficient proportion of the text is
    capitalized."""
    # NOTE(robinson) - Currently limiting this to only sections of text with one sentence.
    # The assumption is that sections with multiple sentences are not titles.
    if sentence_count(text, 3) > 1:
        logger.debug(f"Text does not contain multiple sentences:\n\n{text}")
        return False

    tokens = word_tokenize(text)
    capitalized = sum([word.istitle() or word.isupper() for word in tokens])
    ratio = capitalized / len(tokens)
    return ratio > threshold
