from typing import List
from unstructured.utils import requires_dependencies

import iso639

PYTESSERACT_LANGS = ['afr', 'amh', 'ara', 'asm', 'aze', 'aze_cyrl', 'bel', 'ben', 'bod', 'bos', 'bre', 'bul', 'cat', 'ceb', 'ces', 'chi_sim', 'chi_sim_vert', 'chi_tra', 'chi_tra_vert', 'chr', 'cos', 'cym', 'dan', 'deu', 'div', 'dzo', 'ell', 'eng', 'enm', 'epo', 'equ', 'est', 'eus', 'fao', 'fas', 'fil', 'fin', 'fra', 'frk', 'frm', 'fry', 'gla', 'gle', 'glg', 'grc', 'guj', 'hat', 'heb', 'hin', 'hrv', 'hun', 'hye', 'iku', 'ind', 'isl', 'ita', 'ita_old', 'jav', 'jpn', 'jpn_vert', 'kan', 'kat', 'kat_old', 'kaz', 'khm', 'kir', 'kmr', 'kor', 'kor_vert', 'lao', 'lat', 'lav', 'lit', 'ltz', 'mal', 'mar', 'mkd', 'mlt', 'mon', 'mri', 'msa', 'mya', 'nep', 'nld', 'nor', 'oci', 'ori', 'osd', 'pan', 'pol', 'por', 'pus', 'que', 'ron', 'rus', 'san', 'sin', 'slk', 'slv', 'snd', 'snum', 'spa', 'spa_old', 'sqi', 'srp', 'srp_latn', 'sun', 'swa', 'swe', 'syr', 'tam', 'tat', 'tel', 'tgk', 'tha', 'tir', 'ton', 'tur', 'uig', 'ukr', 'urd', 'uzb', 'uzb_cyrl', 'vie', 'yid', 'yor']


def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    """
    Convert the languages param (list of strings) into tesseract ocr langcode format (uses +) string
    """
    # NOTE(Shreya): assumes language codes are already in tesseract format (will be updated later)

    return "+".join(languages)


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    """
    Convert ocr_languages parameter to list of langcode strings.
    Assumption: ocr_languages is in tesseract plus sign format
    """

    return ocr_languages.split("+")




# TODO(shreya): make list or dict of tesseract langs
# dict language name -> lang code, or std lang to lang code
# SOLUTION print(pytesseract.get_languages(config=''))
# no still need a mapping from some standard language code (anything found in the lang object) to these codes
# for now adding list to top of this file

# convert a language to its tesseract recognized langcode(s), if supported
@requires_dependencies("pytesseract")
def convert_language_to_tesseract(lang: str):

    # if language is already tesseract langcode, return it
    # NOTE: this may catch some of the cases of choosing between a plain vs suffixed tesseract code
    if lang in PYTESSERACT_LANGS:
        return lang
    
    # tesseract uses 3 digit codes as prefix, with suffixes for orthography
    lang_3letters = lang[:3].lower()
    # get iso639 language object
    try:
        lang_iso639 = iso639.Language.match(lang_3letters)
        print(f'{lang} Language Object: {lang_iso639}')
    except:
        # not a valid language
        print(f"{lang} is not a valid language code")
        return ""
    

    # TODO(shreya): catch if lang_iso639 not found/valid

    # match to closest (?) tesseract code
    # NOTE(shreya): what about the special nonstandard cases (ex. chi_tra? there is no chi in tesseract)
    # solution, put both and let it trickle down through language options

    # match to first 3 letters
    pytesseract_langs_3 = [lang[:3] for lang in PYTESSERACT_LANGS] 
    
    # try to match 639-3 (part3)
    if lang_iso639.part3 in pytesseract_langs_3:
        print("match in part3")
        # get all tess langs with this prefix
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part3)
        if lang_iso639.part3 in matched_langcodes: #exact match
            return lang_iso639.part3
        else:
            # return all? check performance
            return prepare_languages_for_tesseract(matched_langcodes)

    # try to match 639-2b (part2b)
    elif lang_iso639.part2b in pytesseract_langs_3:
        print("match in part2b")
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2b)
        if lang_iso639.part3 in matched_langcodes: #exact match
            return lang_iso639.part3
        else:
            # return all? check performance
            return prepare_languages_for_tesseract(matched_langcodes)
    # try to match 639-2t
    elif lang_iso639.part2t in pytesseract_langs_3:
        print("match in part2t")
        matched_langcodes = _get_all_tesseract_langcodes_with_prefix(lang_iso639.part2t)
        if lang_iso639.part3 in matched_langcodes: #exact match
            return lang_iso639.part3
        else:
            # return all? check performance
            return prepare_languages_for_tesseract(matched_langcodes)

    else:
        # warning of no match?
        print("no match to tesseract")
        # run with no lang, or err?
        return ""

    # warning/error if not found: lang not supported by tesseract. link to full list of supported langs
    # https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html



def _get_all_tesseract_langcodes_with_prefix(prefix: str): 
    matched_langcodes = [langcode for langcode in PYTESSERACT_LANGS if langcode.startswith(prefix)]

    # add this check here instead of outside in each case?
    # if prefix in matched_langcodes: #exact match
    #     return prefix
    # else:
    #     return prepare_languages_for_tesseract(matched_langcodes)
    
    return matched_langcodes
