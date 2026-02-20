from unstructured.nlp import tokenize


def test_pos_tag():
    parts_of_speech = tokenize.pos_tag("ITEM 2A. PROPERTIES")
    tags = dict(parts_of_speech)
    assert "ITEM" in tags
    assert "PROPERTIES" in tags
    assert all(isinstance(t, tuple) and len(t) == 2 for t in parts_of_speech)


def test_word_tokenize_caches():
    tokenize.word_tokenize.cache_clear()
    assert tokenize.word_tokenize.cache_info().currsize == 0
    tokenize.word_tokenize("Greetings! I am from outer space.")
    assert tokenize.word_tokenize.cache_info().currsize == 1
    tokenize.word_tokenize("Greetings! I am from outer space.")
    assert tokenize.word_tokenize.cache_info().hits == 1


def test_sent_tokenize_caches():
    tokenize._tokenize_for_cache.cache_clear()
    assert tokenize._tokenize_for_cache.cache_info().currsize == 0
    tokenize._tokenize_for_cache("Greetings! I am from outer space.")
    assert tokenize._tokenize_for_cache.cache_info().currsize == 1
    tokenize._tokenize_for_cache("Greetings! I am from outer space.")
    assert tokenize._tokenize_for_cache.cache_info().hits == 1


def test_pos_tag_caches():
    tokenize.pos_tag.cache_clear()
    assert tokenize.pos_tag.cache_info().currsize == 0
    tokenize.pos_tag("Greetings! I am from outer space.")
    assert tokenize.pos_tag.cache_info().currsize == 1
    tokenize.pos_tag("Greetings! I am from outer space.")
    assert tokenize.pos_tag.cache_info().hits == 1


def test_tokenizers_functions_run():
    sentence = "I am a big brown bear. What are you?"
    tokenize.sent_tokenize(sentence)
    tokenize.word_tokenize(sentence)
    tokenize.pos_tag(sentence)
