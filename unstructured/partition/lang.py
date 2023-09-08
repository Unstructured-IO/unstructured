from typing import List


# convert language param (list of strings) into tesseract ocr language format (639-2 variant joined by + signs)
# NOTE(Shreya): does this arg need a default value?
def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    # NOTE(Shreya): assumes language codes are in tesseract format (will be updated later)
    tesseract_languages = ""
    for lang in languages:
        tesseract_languages = tesseract_languages + lang + "+"

    return tesseract_languages[:-1]  # remove excess plus sign


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    # assumption: ocr_languages is in tesseract plus sign format
    languages = []

    end = False
    while not end:
        plus_sign_index = ocr_languages.find("+")
        if plus_sign_index != -1:
            lang = ocr_languages[:plus_sign_index]
            ocr_languages = ocr_languages[plus_sign_index + 1 :]
        else:  # no plus sign found
            lang = ocr_languages  # entire string is one language
            end = True

        languages.append(lang)

    return languages
