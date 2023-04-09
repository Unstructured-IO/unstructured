import os
import pathlib
from typing import List, Set

DIRECTORY = pathlib.Path(__file__).parent.resolve()
# NOTE(robinson) - the list of English words is based on the nlkt.corpus.words corpus
# and the list of English words found here at the link below. Add more words to the text
# file if needed.
# ref: https://github.com/jeremy-rifkin/Wordlist
ENGLISH_WORDS_FILE = os.path.join(DIRECTORY, "english-words.txt")

with open(ENGLISH_WORDS_FILE) as f:
    BASE_ENGLISH_WORDS = f.read().split("\n")

# NOTE(robinson) - add new words that we want to pass for the English check in here
ADDITIONAL_ENGLISH_WORDS: List[str] = []
ENGLISH_WORDS: Set[str] = set(BASE_ENGLISH_WORDS + ADDITIONAL_ENGLISH_WORDS)
