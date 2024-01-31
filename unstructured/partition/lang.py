import re
from typing import Iterable, Iterator, List, Optional, Union

import iso639
from langdetect import DetectorFactory, detect_langs, lang_detect_exception

from unstructured.documents.elements import Element
from unstructured.logger import logger
from unstructured.partition.utils.constants import (
    TESSERACT_LANGUAGES_AND_CODES,
    TESSERACT_LANGUAGES_SPLITTER,
)

# pytesseract.get_languages(config="") only shows user installed language packs,
# so manually include the list of all currently supported Tesseract languages
PYTESSERACT_LANG_CODES = [
    "afr",
    "amh",
    "ara",
    "asm",
    "aze",
    "aze_cyrl",
    "bel",
    "ben",
    "bod",
    "bos",
    "bre",
    "bul",
    "cat",
    "ceb",
    "ces",
    "chi_sim",
    "chi_sim_vert",
    "chi_tra",
    "chi_tra_vert",
    "chr",
    "cos",
    "cym",
    "dan",
    "deu",
    "div",
    "dzo",
    "ell",
    "eng",
    "enm",
    "epo",
    "equ",
    "est",
    "eus",
    "fao",
    "fas",
    "fil",
    "fin",
    "fra",
    "frk",
    "frm",
    "fry",
    "gla",
    "gle",
    "glg",
    "grc",
    "guj",
    "hat",
    "heb",
    "hin",
    "hrv",
    "hun",
    "hye",
    "iku",
    "ind",
    "isl",
    "ita",
    "ita_old",
    "jav",
    "jpn",
    "jpn_vert",
    "kan",
    "kat",
    "kat_old",
    "kaz",
    "khm",
    "kir",
    "kmr",
    "kor",
    "kor_vert",
    "lao",
    "lat",
    "lav",
    "lit",
    "ltz",
    "mal",
    "mar",
    "mkd",
    "mlt",
    "mon",
    "mri",
    "msa",
    "mya",
    "nep",
    "nld",
    "nor",
    "oci",
    "ori",
    "osd",
    "pan",
    "pol",
    "por",
    "pus",
    "que",
    "ron",
    "rus",
    "san",
    "sin",
    "slk",
    "slv",
    "snd",
    "snum",
    "spa",
    "spa_old",
    "sqi",
    "srp",
    "srp_latn",
    "sun",
    "swa",
    "swe",
    "syr",
    "tam",
    "tat",
    "tel",
    "tgk",
    "tha",
    "tir",
    "ton",
    "tur",
    "uig",
    "ukr",
    "urd",
    "uzb",
    "uzb_cyrl",
    "vie",
    "yid",
    "yor",
]


def prepare_languages_for_tesseract(languages: Optional[List[str]] = ["eng"]) -> str:
    """
    Entry point: convert languages (list of strings) into tesseract ocr langcode format (uses +)
    """
    if languages is None:
        raise ValueError("`languages` can not be `None`")
    converted_languages = list(
        filter(
            lambda x: x is not None and x != "",
            [_convert_language_code_to_pytesseract_lang_code(lang) for lang in languages],
        ),
    )
    # Remove duplicates from the list but keep the original order
    converted_languages = list(dict.fromkeys(converted_languages))
    if len(converted_languages) == 0:
        logger.warning(
            "Failed to find any valid standard language code from "
            f"languages: {languages}, proceed with `eng` instead.",
        )
        return "eng"

    return TESSERACT_LANGUAGES_SPLITTER.join(converted_languages)


def check_language_args(languages: list[str], ocr_languages: Optional[str]) -> Optional[list[str]]:
    """Handle users defining both `ocr_languages` and `languages`, giving preference to `languages`
    and converting `ocr_languages` if needed, but defaulting to `None.

    `ocr_languages` is only a parameter for `auto.partition`, `partition_image`, & `partition_pdf`.
    `ocr_languages` should not be defined as 'auto' since 'auto' is intended for language detection
    which is not supported by `partition_image` or `partition_pdf`."""
    # --- Clean and update defaults
    if ocr_languages:
        ocr_languages = _clean_ocr_languages_arg(ocr_languages)
        logger.warning(
            "The ocr_languages kwarg will be deprecated in a future version of unstructured. "
            "Please use languages instead.",
        )

    if ocr_languages and "auto" in ocr_languages:
        raise ValueError(
            "`ocr_languages` is deprecated but was used to extract text from pdfs and images."
            " The 'auto' argument is only for language *detection* when it is assigned"
            " to `languages` and partitioning documents other than pdfs or images."
            " Language detection is not currently supported in pdfs or images."
        )

    if not isinstance(languages, list):
        raise TypeError(
            "The language parameter must be a list of language codes as strings, ex. ['eng']",
        )

    # --- If `languages` is a null/default value and `ocr_languages` is defined, use `ocr_languages`
    if ocr_languages and (languages == ["auto"] or languages == [""] or not languages):
        languages = ocr_languages.split(TESSERACT_LANGUAGES_SPLITTER)
        logger.warning(
            "Only one of languages and ocr_languages should be specified. "
            "languages is preferred. ocr_languages is marked for deprecation.",
        )

    # --- Clean `languages`
    # If "auto" is included in the list of inputs, language detection will be triggered downstream.
    # The rest of the inputted languages are ignored.
    if languages:
        if "auto" not in languages:
            for i, lang in enumerate(languages):
                languages[i] = TESSERACT_LANGUAGES_AND_CODES.get(lang.lower(), lang)

            str_languages = _clean_ocr_languages_arg(languages)
            if not str_languages:
                return None
            languages = str_languages.split(TESSERACT_LANGUAGES_SPLITTER)
        # else, remove the extraneous languages.
        # NOTE (jennings): "auto" should only be used for partitioners OTHER THAN `_pdf` or `_image`
        else:
            # define as 'auto' for language detection when partitioning non-pdfs or -images
            languages = ["auto"]
        return languages

    return None


def convert_old_ocr_languages_to_languages(ocr_languages: str) -> list[str]:
    """
    Convert ocr_languages parameter to list of langcode strings.
    Assumption: ocr_languages is in tesseract plus sign format
    """

    return ocr_languages.split(TESSERACT_LANGUAGES_SPLITTER)


def _convert_language_code_to_pytesseract_lang_code(lang: str) -> str:
    """
    Convert a single language code to its tesseract formatted and recognized
    langcode(s), if supported.
    """
    # if language is already tesseract langcode, return it immediately
    # this will catch the tesseract special cases equ and osd
    # NOTE(shreya): this may catch some cases of choosing between tesseract code variants for a lang
    if lang in PYTESSERACT_LANG_CODES:
        return lang

    lang_iso639 = _get_iso639_language_object(lang)

    # tesseract uses 3 digit codes (639-3, 639-2b, etc) as prefixes, with suffixes for orthography
    # use first 3 letters of tesseract codes for matching to standard codes
    pytesseract_langs_3 = {lang[:3] for lang in PYTESSERACT_LANG_CODES}

    if lang_iso639:
        # try to match ISO 639-3 code
        if lang_iso639.part3 in pytesseract_langs_3:
            matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part3)
            return TESSERACT_LANGUAGES_SPLITTER.join(matched_langcodes)

        # try to match ISO 639-2b
        elif lang_iso639.part2b in pytesseract_langs_3:
            matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2b)
            return TESSERACT_LANGUAGES_SPLITTER.join(matched_langcodes)

        # try to match ISO 639-2t
        elif lang_iso639.part2t in pytesseract_langs_3:
            matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2t)
            return TESSERACT_LANGUAGES_SPLITTER.join(matched_langcodes)

        else:
            logger.warning(f"{lang} is not a language supported by Tesseract.")
            return ""
    logger.warning(f"{lang} is not a language supported by Tesseract.")
    return ""


def _get_iso639_language_object(lang: str) -> Optional[iso639.Language]:
    try:
        return iso639.Language.match(lang.lower())
    except iso639.LanguageNotFoundError:
        logger.warning(f"{lang} is not a valid standard language code.")
        return None


def _get_all_tesseract_langcodes_with_prefix(prefix: str) -> list[str]:
    """
    Get all matching tesseract langcodes with this prefix (may be one or multiple variants).
    """
    return [langcode for langcode in PYTESSERACT_LANG_CODES if langcode.startswith(prefix)]


def detect_languages(
    text: str,
    languages: Optional[List[str]] = ["auto"],
) -> Optional[List[str]]:
    """
    Detects the list of languages present in the text (in the default "auto" mode),
    or formats and passes through the user inputted document languages if provided.
    """
    if not isinstance(languages, list):
        raise TypeError(
            'The language parameter must be a list of language codes as strings, ex. ["eng"]',
        )

    # Skip language detection for partitioners that use other partitioners.
    # For example, partition_msg relies on partition_html and partition_text, but the metadata
    # gets overwritten after elements have been returned by _html and _text,
    # so `languages` would be detected twice.
    # Also return None if there is no text.
    if languages[0] == "" or text.strip() == "":
        return None

    # If text contains special characters (like ñ, å, or Korean/Mandarin/etc.) it will NOT default
    # to English. It will default to English if text is only ascii characters and is short.
    if re.match(r"^[\x00-\x7F]+$", text) and len(text.split()) < 5:
        return ["eng"]

    # set seed for deterministic langdetect outputs
    DetectorFactory.seed = 0

    doc_languages: list[str] = []

    # user inputted languages:
    # if "auto" is included in the list of inputs, language detection will be triggered
    # and the rest of the inputted languages will be ignored
    if languages and "auto" not in languages:
        for lang in languages:
            str_lang = TESSERACT_LANGUAGES_AND_CODES.get(lang.lower(), lang)
            language = _get_iso639_language_object(str_lang[:3])
            if language:
                doc_languages.append(language.part3)

    # language detection:
    else:
        # warn if any values other than "auto" were provided
        if len(languages) > 1:
            logger.warning(
                f'Since "auto" is present in the input languages provided ({languages}), '
                "the language will be auto detected and the rest of the inputted "
                "languages will be ignored.",
            )

        try:
            langdetect_result = detect_langs(text)
        except lang_detect_exception.LangDetectException as e:
            logger.warning(e)
            return None  # None as default

        langdetect_langs: list[str] = []

        # NOTE(robinson) - Chinese gets detected with codes zh-cn, zh-tw, zh-hk for various
        # Chinese variants. We normalizes these because there is a single model for Chinese
        # machine translation
        # TODO(shreya): decide how to maintain nonstandard chinese script information
        for langobj in langdetect_result:
            if str(langobj.lang).startswith("zh"):
                langdetect_langs.append("zho")
            else:
                language = _get_iso639_language_object(langobj.lang[:3])
                if language:
                    langdetect_langs.append(language.part3)

        # remove duplicate chinese (if exists) without modifying order
        for lang in langdetect_langs:
            if lang not in doc_languages:
                doc_languages.append(lang)

    return doc_languages


def apply_lang_metadata(
    elements: Iterable[Element],
    languages: Optional[List[str]],
    detect_language_per_element: bool = False,
) -> Iterator[Element]:
    """Detect language and apply it to metadata.languages for each element in `elements`.
    If languages is None, default to auto detection.
    If languages is and empty string, skip."""
    # -- Note this function has a stream interface, but reads the full `elements` stream into memory
    # -- before emitting the first updated element as output.

    # The auto `partition` function uses `None` as a default because the default for
    # `partition_pdf` and `partition_img` conflict with the other partitioners that use ["auto"]
    if languages is None:
        languages = ["auto"]

    # Skip language detection for partitioners that use other partitioners.
    # For example, partition_msg relies on partition_html and partition_text, but the metadata
    # gets overwritten after elements have been returned by _html and _text,
    # so `languages` would be detected twice.
    if languages == [""]:
        yield from elements
        return

    # Convert elements to a list to get the text, detect the language, and add it to the elements
    if not isinstance(elements, List):
        elements = list(elements)

    full_text = " ".join(e.text for e in elements if hasattr(e, "text"))
    detected_languages = detect_languages(text=full_text, languages=languages)
    if (
        detected_languages is not None
        and len(languages) == 1
        and detect_language_per_element is False
    ):
        # -- apply detected language to each element's metadata --
        for e in elements:
            e.metadata.languages = detected_languages
            yield e
    else:
        for e in elements:
            if hasattr(e, "text"):
                e.metadata.languages = detect_languages(e.text)
                yield e
            else:
                yield e


def _clean_ocr_languages_arg(ocr_languages: Union[List[str], str]) -> str:
    """Fix common incorrect definitions for ocr_languages:
    defining it as a list, adding extra quotation marks, adding brackets.
    Returns a single string of ocr_languages"""
    # extract from list
    if isinstance(ocr_languages, list):
        ocr_languages = "+".join(ocr_languages)

    # remove extra quotations
    ocr_languages = re.sub(r"[\"']", "", ocr_languages)
    # remove brackets
    ocr_languages = re.sub(r"[\[\]]", "", ocr_languages)

    return ocr_languages
