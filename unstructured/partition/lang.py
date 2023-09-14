from typing import List

import iso639

from unstructured.utils import requires_dependencies

# TODO(shreya): make the call below and use regex to format it into list of strings instead of hardcoding it here
# print(pytesseract.get_languages(config=''))

# TODO(shreya): decide if these tesseract langs should be stored as a list or a mapping
# mapping ideas: 
# standard language code -> tess lang (many to 1), 
# standard code to list of tess langs in the same language (1 to list)
# language name -> tess lang or list of tess langs
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


def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    """
    Convert the languages param (list of strings) into tesseract ocr langcode format (uses +) string
    """
    return "+".join([convert_language_to_tesseract(lang) for lang in languages])


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    """
    Convert ocr_languages parameter to list of langcode strings.
    Assumption: ocr_languages is in tesseract plus sign format
    """

    return ocr_languages.split("+")


# convert a language to its tesseract formatted and recognized langcode(s), if supported
@requires_dependencies("pytesseract")
def convert_language_to_tesseract(lang: str) -> str:
    # if language is already tesseract langcode, return it immediately
    # NOTE(shreya): this may catch some of the cases of choosing between a plain vs suffixed tesseract code
    if lang in PYTESSERACT_LANGS:
        return lang

    # tesseract uses 3 digit codes as prefix, with suffixes for orthography
    lang_3letters = lang[:3].lower()
    # get iso639 language object
    try:
        lang_iso639 = iso639.Language.match(lang_3letters)
        print(f"{lang} Language Object: {lang_iso639}")
    except:
        # not a valid language
        # TODO(shreya): warn or raise? or proceed somehow?
        print(f"{lang} is not a valid language code.")
        return ""

    # match to first 3 letters of tesseract codes
    pytesseract_langs_3 = [lang[:3] for lang in PYTESSERACT_LANGS]

    # try to match 639-3 (part3)
    if lang_iso639.part3 in pytesseract_langs_3:
        print("match in part3")
        # get all tess langs with this prefix (can be one or multiple_)
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part3)
        return prepare_languages_for_tesseract(matched_langcodes)

    # try to match 639-2b (part2b)
    elif lang_iso639.part2b in pytesseract_langs_3:
        print("match in part2b")
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2b)
        return prepare_languages_for_tesseract(matched_langcodes)

    # try to match 639-2t
    elif lang_iso639.part2t in pytesseract_langs_3:
        print("match in part2t")
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2t)
        return prepare_languages_for_tesseract(matched_langcodes)

    else:
        # no match from the standard language code to a tesseract lang
        # warning/error if not found: lang not supported by tesseract. link to full list of supported langs
        # https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html ?
        # TODO(shreya): warn or raise? or proceed somehow?
        print(f"{lang} is not a language supported by Tesseract.")
        
        # run with no lang, or err?
        return ""


def _get_all_tesseract_langcodes_with_prefix(prefix: str):
    return [langcode for langcode in PYTESSERACT_LANGS if langcode.startswith(prefix)]
