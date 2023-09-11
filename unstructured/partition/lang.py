from typing import List


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
