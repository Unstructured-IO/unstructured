from nltk.corpus import words as nltk_words

ADDITIONAL_ENGLISH_WORDS = [
    "unstructured",
    "technologies",
]
ENGLISH_WORDS = nltk_words.words() + ADDITIONAL_ENGLISH_WORDS
