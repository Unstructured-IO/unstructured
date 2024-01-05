import os
from enum import Enum


class Source(Enum):
    PDFMINER = "pdfminer"
    OCR_TESSERACT = "ocr_tesseract"
    OCR_PADDLE = "ocr_paddle"


class OCRMode(Enum):
    INDIVIDUAL_BLOCKS = "individual_blocks"
    FULL_PAGE = "entire_page"


class PartitionStrategy:
    AUTO = "auto"
    FAST = "fast"
    OCR_ONLY = "ocr_only"
    HI_RES = "hi_res"


SORT_MODE_XY_CUT = "xy-cut"
SORT_MODE_BASIC = "basic"
SORT_MODE_DONT = "dont"

OCR_AGENT_TESSERACT = "tesseract"
OCR_AGENT_PADDLE = "paddle"

SUBREGION_THRESHOLD_FOR_OCR = 0.5
UNSTRUCTURED_INCLUDE_DEBUG_METADATA = os.getenv("UNSTRUCTURED_INCLUDE_DEBUG_METADATA", False)

# Note(yuming): Default language for paddle OCR
# soon will be able to specify the language down through partition() as well
DEFAULT_PADDLE_LANG = os.getenv("DEFAULT_PADDLE_LANG", "en")

# this field is defined by pytesseract/unstructured.pytesseract
TESSERACT_TEXT_HEIGHT = "height"

TESSERACT_LANGUAGES_SPLITTER: str = "+"

# source: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html
# All languages have been changed to lowercase and have been altered to remove dates and "(contrib)"
# Ex: "Greek, Ancient (to 1453) (contrib)" -> "greek, ancient"
# Where it seemed appropriate, languages have been split into multiple keys with the same value.
# Ex: "greek, modern":"ell", "greek":"ell", "chinese - simplified":"chi_sim", "chinese":"chi_sim",
# On tesseract-ocr.github.io, "Spanish" matches with both "spa_old" and "spa".
# Here, it only matches with "spa" and "spanish - old":"spa_old" was added.
TESSERACT_LANGUAGES_AND_CODES = {
    "afrikaans": "afr",
    "amharic": "amh",
    "arabic": "ara",
    "assamese": "asm",
    "azerbaijani": "aze",
    "azerbaijani - cyrilic": "aze_cyrl",
    "belarusian": "bel",
    "bengali": "ben",
    "tibetan": "bod",
    "bosnian": "bos",
    "breton": "bre",
    "bulgarian": "bul",
    "catalan; Valencian": "cat",
    "cebuano": "ceb",
    "czech": "ces",
    "chinese - simplified": "chi_sim",
    "chinese": "chi_sim",
    "chinese - traditional": "chi_tra",
    "cherokee": "chr",
    "corsican": "cos",
    "welsh": "cym",
    "danish": "dan",
    "danish - fraktur": "dan_frak",
    "german": "deu",
    "german - fraktur (contrib)": "deu_frak",  # "contrib" not removed because it would repeat key
    "dzongkha": "dzo",
    "greek, modern": "ell",
    "greek": "ell",
    "english": "eng",
    "english, middle": "enm",
    "esperanto": "epo",
    "math / equation detection module": "equ",
    "estonian": "est",
    "basque": "eus",
    "faroese": "fao",
    "persian": "fas",
    "filipino (old - tagalog)": "fil",
    "filipino": "fil",
    "finnish": "fin",
    "french": "fra",
    "german - fraktur": "frk",
    "french, middle": "frm",
    "western frisian": "fry",
    "scottish gaelic": "gla",
    "irish": "gle",
    "galician": "glg",
    "greek, ancient": "grc",
    "gujarati": "guj",
    "haitian": "hat",
    "haitian creole": "hat",
    "hebrew": "heb",
    "hindi": "hin",
    "croatian": "hrv",
    "hungarian": "hun",
    "armenian": "hye",
    "inuktitut": "iku",
    "indonesian": "ind",
    "icelandic": "isl",
    "italian": "ita",
    "italian - old": "ita_old",
    "javanese": "jav",
    "japanese": "jpn",
    "kannada": "kan",
    "georgian": "kat",
    "georgian - old": "kat_old",
    "kazakh": "kaz",
    "central khmer": "khm",
    "kirghiz": "kir",
    "kyrgyz": "kir",
    "kurmanji (kurdish - latin script)": "kmr",
    "korean": "kor",
    "korean (vertical)": "kor_vert",
    "kurdish (arabic script)": "kur",
    "lao": "lao",
    "latin": "lat",
    "latvian": "lav",
    "lithuanian": "lit",
    "luxembourgish": "ltz",
    "malayalam": "mal",
    "marathi": "mar",
    "macedonian": "mkd",
    "maltese": "mlt",
    "mongolian": "mon",
    "maori": "mri",
    "malay": "msa",
    "burmese": "mya",
    "nepali": "nep",
    "dutch": "nld",
    "flemish": "nld",
    "norwegian": "nor",
    "occitan": "oci",
    "oriya": "ori",
    "orientation and script detection module": "osd",
    "panjabi": "pan",
    "punjabi": "pan",
    "polish": "pol",
    "portuguese": "por",
    "pushto": "pus",
    "pashto": "pus",
    "quechua": "que",
    "romanian": "ron",
    "moldavian": "ron",
    "moldovan": "ron",
    "russian": "rus",
    "sanskrit": "san",
    "sinhala": "sin",
    "sinhalese": "sin",
    "slovak": "slk",
    "slovak - fraktur": "slk_frak",
    "slovenian": "slv",
    "sindhi": "snd",
    "spanish": "spa",
    "castilian": "spa",
    "spanish - old": "spa_old",
    "castilian - old": "spa_old",
    "albanian": "sqi",
    "serbian": "srp",
    "serbian - latin": "srp_latn",
    "sundanese": "sun",
    "swahili": "swa",
    "swedish": "swe",
    "syriac": "syr",
    "tamil": "tam",
    "tatar": "tat",
    "telugu": "tel",
    "tajik": "tgk",
    "tagalog": "tgl",
    "thai": "tha",
    "tigrinya": "tir",
    "tonga": "ton",
    "turkish": "tur",
    "uighur": "uig",
    "uyghur": "uig",
    "ukrainian": "ukr",
    "urdu": "urd",
    "uzbek": "uzb",
    "uzbek - cyrilic": "uzb_cyrl",
    "vietnamese": "vie",
    "yiddish": "yid",
    "yoruba": "yor",
}

# 2 ** 31 - 1, max byte size for image data
TESSERACT_MAX_SIZE = 2147483647

# default image colors
IMAGE_COLOR_DEPTH = 32
