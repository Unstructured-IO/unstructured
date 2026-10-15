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


def test_the_spacy_pipeline_runs_once_per_distinct_text(monkeypatch):
    """`_process` is the only expensive call in this module and every public helper needs it.

    `is_possible_narrative_text` reaches it three times for one string -- via `sent_tokenize`,
    `word_tokenize` and `pos_tag` -- and each produced an identical `Doc`. The per-helper caches
    hide the repetition from their own callers but not from spaCy.
    """
    from unstructured.partition.text_type import is_possible_narrative_text

    _clear_tokenize_caches()
    runs = _count_pipeline_runs(monkeypatch)

    is_possible_narrative_text("Paragraph number 7 with some filler text in it.")

    assert runs["n"] == 1, f"spaCy pipeline ran {runs['n']} times for one string"


def test_repeated_text_does_not_re_run_the_pipeline(monkeypatch):
    """Headers, footers and boilerplate repeat across a document."""
    _clear_tokenize_caches()
    runs = _count_pipeline_runs(monkeypatch)

    for _ in range(5):
        tokenize.word_tokenize("Confidential -- internal use only.")
        tokenize.pos_tag("Confidential -- internal use only.")

    assert runs["n"] == 1


def test_oversized_text_bypasses_the_doc_cache(monkeypatch):
    """A `Doc` is much heavier than the token lists the other caches hold.

    Caching one built from a multi-megabyte element would pin that cost for the life of the
    process, so past the threshold the pipeline is run without memoizing the result.
    """
    _clear_tokenize_caches()
    runs = _count_pipeline_runs(monkeypatch)
    oversized = "word " * ((tokenize.MAX_CACHEABLE_CHARS // 5) + 1)
    assert len(oversized) > tokenize.MAX_CACHEABLE_CHARS

    tokenize._process(oversized)
    tokenize._process(oversized)

    assert runs["n"] == 2, "oversized text should not be memoized"
    assert tokenize._process_cached.cache_info().currsize == 0


def test_text_at_the_threshold_is_still_cached(monkeypatch):
    _clear_tokenize_caches()
    runs = _count_pipeline_runs(monkeypatch)
    sized = "a" * tokenize.MAX_CACHEABLE_CHARS

    tokenize._process(sized)
    tokenize._process(sized)

    assert runs["n"] == 1


def _clear_tokenize_caches() -> None:
    for cached in (
        tokenize.word_tokenize,
        tokenize.pos_tag,
        tokenize._tokenize_for_cache,
        tokenize._process_cached,
    ):
        cached.cache_clear()


def _count_pipeline_runs(monkeypatch) -> dict[str, int]:
    """Count trips into spaCy itself, below every cache in this module.

    The counter wraps the `Language` object rather than `_process`, so it still measures real
    pipeline work once `_process` is itself cached. Patching `nlp.__call__` on the instance does
    not work -- Python resolves dunders on the type.
    """
    runs = {"n": 0}
    real_nlp = tokenize._get_nlp()

    class CountingNlp:
        max_length = real_nlp.max_length

        def __call__(self, text, *args, **kwargs):
            runs["n"] += 1
            return real_nlp(text, *args, **kwargs)

    monkeypatch.setattr(tokenize, "_get_nlp", lambda: CountingNlp())
    return runs
