from typing import List


# convert language param (list of strings) into tesseract ocr language format (639-2/b variant joined by + signs)
def prepare_languages_for_tesseract(languages: List[str] = ["eng"]):
    tesseract_languages = ""
    for lang in languages: 
        tesseract_languages = tesseract_languages + lang + "+"

    return tesseract_languages[:-1] # remove excess plus sign

