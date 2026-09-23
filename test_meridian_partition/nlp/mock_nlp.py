from typing import List, Tuple


def mock_sent_tokenize(text: str) -> List[str]:
    sentences = text.split(".")
    return sentences[:-1] if text.endswith(".") else sentences


def mock_word_tokenize(text: str) -> List[str]:
    return text.split(" ")


def mock_pos_tag(text: str) -> List[Tuple[str, str]]:
    tokens = mock_word_tokenize(text)
    pos_tags: List[Tuple[str, str]] = []
    for token in tokens:
        if token.lower() == "ask":
            pos_tags.append((token, "VB"))
        else:
            pos_tags.append((token, ""))
    return pos_tags
