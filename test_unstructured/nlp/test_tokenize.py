import contextlib
import sysconfig
from pathlib import Path

import pytest

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


def _model_is_missing(*_args, **_kwargs):
    """Stand-in for `spacy.load` when the pinned model is not installed."""
    raise OSError("no such model")


def _model_load_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `spacy.load` and the install lock cheap, so only the decision is under test."""
    monkeypatch.setattr(tokenize, "spacy", type("FakeSpacy", (), {"load": _model_is_missing}))
    monkeypatch.setattr(tokenize, "FileLock", lambda *args, **kwargs: contextlib.nullcontext())


def test_auto_install_can_be_disabled(monkeypatch: pytest.MonkeyPatch):
    """Air-gapped deployments must be able to fail instead of downloading at runtime."""
    installs = []

    _model_load_fails(monkeypatch)
    monkeypatch.setenv("UNSTRUCTURED_SPACY_AUTO_INSTALL", "false")
    monkeypatch.setattr(tokenize, "_install_spacy_model", lambda: installs.append("installed"))

    with pytest.raises(RuntimeError, match="UNSTRUCTURED_SPACY_AUTO_INSTALL"):
        tokenize._load_spacy_model()

    assert installs == []


def test_the_install_lock_sits_beside_the_model_it_guards():
    """The lock has to be found by every worker that writes this destination."""
    lock = Path(tokenize._install_lock_path())

    assert lock.parent == Path(sysconfig.get_paths()["purelib"])
    assert lock.name == f"{tokenize._SPACY_MODEL_NAME}.install.lock"


@pytest.mark.parametrize("temp_dir", ["tmp/4321", "tmp/8765"])
def test_the_install_lock_does_not_follow_the_process_temp_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, temp_dir: str
):
    """`GLOBAL_WORKING_DIR_ENABLED` gives each process group its own `tempfile` directory.

    A lock derived from `tempfile.gettempdir()` would then be a different file in every worker
    while they all install into the same site-packages, so two workers could replace the model
    directory under each other. Whatever the running configuration did to `tempfile` -- and
    whether the configuration module was imported before or after this one -- the lock has to
    resolve to one path. This is the import-order half of the regression: the path is a function
    of the destination alone, so there is no order to get wrong.
    """
    fake_tempdir = str(tmp_path / temp_dir)
    monkeypatch.setattr(tokenize.tempfile, "tempdir", fake_tempdir, raising=False)
    monkeypatch.setattr(tokenize.tempfile, "gettempdir", lambda: fake_tempdir, raising=False)
    assert tokenize.tempfile.gettempdir() == fake_tempdir

    assert tokenize._install_lock_path() == str(
        Path(sysconfig.get_paths()["purelib"]) / f"{tokenize._SPACY_MODEL_NAME}.install.lock"
    )


def test_auto_install_disabled_never_takes_the_install_lock(monkeypatch: pytest.MonkeyPatch):
    """Nothing is installed, so the opt-out must not queue behind other installers.

    It also keeps a read-only site-packages from turning the opt-out into a permission error,
    since taking the lock creates the file next to the model.
    """
    locks = []

    _model_load_fails(monkeypatch)
    monkeypatch.setattr(
        tokenize,
        "FileLock",
        lambda *args, **kwargs: locks.append(args[0]) or contextlib.nullcontext(),
    )
    monkeypatch.setenv("UNSTRUCTURED_SPACY_AUTO_INSTALL", "false")

    with pytest.raises(RuntimeError, match="UNSTRUCTURED_SPACY_AUTO_INSTALL"):
        tokenize._load_spacy_model()

    assert locks == []


def test_auto_install_stays_the_default(monkeypatch: pytest.MonkeyPatch):
    """Without the variable the pinned model is still fetched, as it was before."""
    installs = []

    def record_and_fail() -> None:
        installs.append(tokenize._SPACY_MODEL_URL)
        raise RuntimeError("download failed")

    _model_load_fails(monkeypatch)
    monkeypatch.setattr(tokenize, "_install_spacy_model", record_and_fail)
    monkeypatch.delenv("UNSTRUCTURED_SPACY_AUTO_INSTALL", raising=False)

    with pytest.raises(RuntimeError, match="download failed"):
        tokenize._load_spacy_model()

    assert installs == [tokenize._SPACY_MODEL_URL]
