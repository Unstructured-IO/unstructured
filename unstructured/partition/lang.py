from typing import List


# convert language param (list of strings) into tesseract ocr language format (639-2 variant joined by + signs)
def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    # NOTE(Shreya): assumes language codes are in tesseract format (will be updated later)
    
    return "+".join([lang for lang in languages])


def convert_old_ocr_languages_to_languages(ocr_languages: str):
    # assumption: ocr_languages is in tesseract plus sign format
    
    return ocr_languages.split("+")
