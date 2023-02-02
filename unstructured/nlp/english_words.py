import pathlib
import os

DIRECTORY = pathlib.Path(__file__).parent.resolve()
# NOTE(robinson) - the list of English words is based on the nlkt.corpus.words corpus
# and the list of English words found here at the link below. Add more words to the text
# file if needed.
# ref: https://github.com/jeremy-rifkin/Wordlist
ENGLISH_WORDS_FILE = os.path.join(DIRECTORY, "english-words.txt")

with open(ENGLISH_WORDS_FILE, "r") as f:
    ENGLISH_WORDS = f.read().split("\n")
