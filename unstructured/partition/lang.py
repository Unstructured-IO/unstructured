import re
from typing import Iterable, Iterator, List, Optional

import iso639
from langdetect import DetectorFactory, detect_langs, lang_detect_exception

from unstructured.documents.elements import Element
from unstructured.logger import logger

# pytesseract.get_languages(config="") only shows user installed language packs,
# so manually include the list of all currently supported Tesseract languages
PYTESSERACT_LANGS = [
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


def prepare_languages_for_tesseract(languages: Optional[List[str]] = ["eng"]):
    """
    Entry point: convert languages (list of strings) into tesseract ocr langcode format (uses +)
    """
    if languages is None:
        raise ValueError("`languages` can not be `None`")
    converted_languages = list(
        filter(None, [convert_language_to_tesseract(lang) for lang in languages]),
    )
    return "+".join(converted_languages)


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    """
    Convert ocr_languages parameter to list of langcode strings.
    Assumption: ocr_languages is in tesseract plus sign format
    """

    return ocr_languages.split("+")


def convert_language_to_tesseract(lang: str) -> str:
    """
    Convert a language code to its tesseract formatted and recognized langcode(s), if supported.
    """
    # if language is already tesseract langcode, return it immediately
    # this will catch the tesseract special cases equ and osd
    # NOTE(shreya): this may catch some cases of choosing between tesseract code variants for a lang
    if lang in PYTESSERACT_LANGS:
        return lang

    # get iso639 language object
    try:
        lang_iso639 = iso639.Language.match(lang.lower())
    except iso639.LanguageNotFoundError:
        logger.warning(f"{lang} is not a valid standard language code.")
        return ""

    # tesseract uses 3 digit codes (639-3, 639-2b, etc) as prefixes, with suffixes for orthography
    # use first 3 letters of tesseract codes for matching to standard codes
    pytesseract_langs_3 = {lang[:3] for lang in PYTESSERACT_LANGS}

    # try to match ISO 639-3 code
    if lang_iso639.part3 in pytesseract_langs_3:
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part3)
        return "+".join(matched_langcodes)

    # try to match ISO 639-2b
    elif lang_iso639.part2b in pytesseract_langs_3:
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2b)
        return "+".join(matched_langcodes)

    # try to match ISO 639-2t
    elif lang_iso639.part2t in pytesseract_langs_3:
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2t)
        return "+".join(matched_langcodes)

    else:
        logger.warning(f"{lang} is not a language supported by Tesseract.")
        return ""


def _get_all_tesseract_langcodes_with_prefix(prefix: str):
    """
    Get all matching tesseract langcodes with this prefix (may be one or multiple variants).
    """
    return [langcode for langcode in PYTESSERACT_LANGS if langcode.startswith(prefix)]


def _convert_to_standard_langcode(lang: str) -> str:
    """
    Convert a language code to the standard internal language code format.
    """
    # convert to standard ISO 639-3 language code
    lang_iso639 = iso639.Language.match(lang[:3].lower())
    return lang_iso639.part3


def detect_languages(
    text: str,
    languages: Optional[List[str]] = ["auto"],
) -> List[str]:
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
    if languages[0] == "":
        return [""]

    # Default to "eng" if text is empty or it has only ascii characters and is short
    if text.strip() == "" or (re.match(r"^[\x00-\x7F]+$", text) and len(text) < 20):
        return ["eng"]  # english as default

    # set seed for deterministic langdetect outputs
    DetectorFactory.seed = 0

    # user inputted languages:
    # if "auto" is included in the list of inputs, language detection will be triggered
    # and the rest of the inputted languages will be ignored
    if languages and "auto" not in languages:
        doc_languages = [_convert_to_standard_langcode(lang) for lang in languages]

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
            return ["eng"]  # english as default

        # NOTE(robinson) - Chinese gets detected with codes zh-cn, zh-tw, zh-hk for various
        # Chinese variants. We normalizes these because there is a single model for Chinese
        # machine translation
        # TODO(shreya): decide how to maintain nonstandard chinese script information
        langdetect_langs = [
            _convert_to_standard_langcode("zh")
            if langobj.lang.startswith("zh")
            else _convert_to_standard_langcode(langobj.lang)
            for langobj in langdetect_result
        ]

        # remove duplicate chinese (if exists) without modifying order
        doc_languages = []
        for lang in langdetect_langs:
            if lang not in doc_languages:
                doc_languages.append(lang)

    return doc_languages


def apply_lang_metadata(
    elements: Iterable[Element],
    languages: Optional[List[str]],
    detect_language_per_element: bool = False,
) -> Iterator[Element]:
    """Detect and apply metadata.languages to each element in `elements`."""
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

    if not isinstance(elements, List):
        elements = list(elements)

    full_text = " ".join(e.text for e in elements if hasattr(e, "text"))
    detected_languages = detect_languages(text=full_text, languages=languages)
    if (
        detected_languages is not None
        and len(languages) == 1
        and detect_language_per_element is False
    ):
        # -- apply detected language to each metadata --
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
