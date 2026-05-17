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


def test_process_truncates_text_exceeding_spacy_max_length(caplog):
    # Build text well above spaCy's default 1,000,000-char limit, like the prod trace.
    nlp = tokenize._get_nlp()
    long_text = "This is a sentence. " * ((nlp.max_length // 20) + 10_000)
    assert len(long_text) > nlp.max_length

    with caplog.at_level("WARNING", logger=tokenize.logger.name):
        # Must not raise spacy ValueError E088.
        sents = tokenize.sent_tokenize(long_text)

    assert len(sents) > 0
    assert any("exceeds spaCy max_length" in rec.message for rec in caplog.records)


def test_process_does_not_truncate_text_within_limit():
    nlp = tokenize._get_nlp()
    text = "Greetings! I am from outer space."
    assert len(text) <= nlp.max_length
    doc = tokenize._process(text)
    # When no truncation occurs the full text round-trips through spaCy.
    assert doc.text == text
