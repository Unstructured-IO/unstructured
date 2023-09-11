from typing import List


# convert languages (list of strings) into tesseract ocr langcode format (with +)
def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    # NOTE(Shreya): assumes language codes are in tesseract format (will be updated later)

    return "+".join(languages)


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    # assumption: ocr_languages is in tesseract plus sign format

    return ocr_languages.split("+")
