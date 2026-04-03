from unstructured.metrics.text_extraction import standardize_quotes

SAMPLE_TEXTS = [
    "She said \u201cHello\u201d and then whispered \u2018Goodbye\u2019 before leaving.",
    "\u201eTo be, or not to be, that is the question\u201d - Shakespeare\u2019s famous quote.",
    "\u00abWhen he said \u201clife is beautiful,\u201d I believed him\u00bb wrote Maria.",
    "\u275dDo you remember when we first met?\u275e she asked with a smile.",
    "\u301dThe meeting starts at 10:00, don\u2019t be late!\u301f announced the manager.",
    '\u300cHe told me "This is important" yesterday\u300d, she explained.',
    "\u300eThe sun was setting. The birds were singing. It was peaceful.\u300f",
    "\ufe42Meeting #123 @ 15:00 - Don\u2019t forget!\ufe41",
    "\u300cHello\u300d, \u275dWorld\u275e, \"Test\", 'Example', \u201eQuote\u201d, \u00abFinal\u00bb",  # noqa: E501
    "It\u2019s John\u2019s book, isn\u2019t it?",
    '\u2039Testing the system\u2019s capability for "quoted" text\u203a',
    "\u275bFirst sentence. Second sentence. Third sentence.\u275c",
    "\u300cChapter 1\u300d: \u275dThe Beginning\u275e - \u201eA new story\u201d begins \u00abtoday\u00bb.",  # noqa: E501
]


def run_standardize_quotes():
    for text in SAMPLE_TEXTS:
        standardize_quotes(text)


def test_benchmark_standardize_quotes(benchmark):
    benchmark(run_standardize_quotes)
