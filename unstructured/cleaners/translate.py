from typing import Optional
import warnings

import langdetect
from transformers import MarianMTModel, MarianTokenizer

from unstructured.staging.huggingface import chunk_by_attention_window
from unstructured.nlp.tokenize import sent_tokenize


def _get_opus_mt_model_name(target_lang: str, source_lang: str):
    """Constructs the name of the MarianMT machine translation model based on the
    source and target language."""
    return f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"


def _validate_language_code(language_code: str):
    if not isinstance(language_code, str) or len(language_code) != 2:
        raise ValueError(
            f"Invalid language code: {language_code}. Language codes must be "
            "two letter strings."
        )


def translate_text(text, target_lang: str = "en", source_lang: Optional[str] = None):
    """Translates the foreign language text. Uses the stage

    Parameters
    ----------
    text: str
        The text to translate
    target_lang: str
        The two letter language code for the target langague. Defaults to "en".
    source_lang: Optional[str]
        The two letter language code for the language of the input text. If source_lang is
        not provided, the function will try to detect it.
    """
    _source_lang: str = (
        source_lang if source_lang is not None else langdetect.detect(text)
    )

    _validate_language_code(target_lang)
    _validate_language_code(_source_lang)

    model_name = _get_opus_mt_model_name(target_lang, _source_lang)

    try:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
    except OSError:
        raise ValueError(
            f"Transformers could not find the translation model {model_name}. "
            "The requested source/target language combo is not suppored."
        )

    chunks: List[str] = chunk_by_attention_window(
        text, tokenizer, split_function=sent_tokenize
    )

    translated_chunks: List[str] = list()
    for chunk in chunks:
        translated_chunks.append(_translate_text(text, model, tokenizer))

    return " ".join(translated_chunks)


def _translate_text(text, model, tokenizer):
    """Translates text using the specified model and tokenizer."""
    # NOTE(robinson) - Suppresses the HuggingFace UserWarning resulting from the "max_length"
    # key in the MarianMT config. The warning states that "max_length" will be deprecated
    # in transformers v5
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        translated = model.generate(
            **tokenizer(
                [text], return_tensors="pt", padding="max_length", max_length=512
            )
        )
    return [
        tokenizer.decode(t, max_new_tokens=512, skip_special_tokens=True)
        for t in translated
    ][0]
