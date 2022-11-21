Installation
============

You can install the library by cloning the repo and running ``make install`` from the
root directory. Developers can run ``make install-local`` to install the dev and test
requirements alongside the base requirements. If you want a minimal installation without any
parser specific dependencies, run ``make install-base``.

Logging
-------

You can set the logging level for the package with the ``LOG_LEVEL`` environment variable.
By default, the log level is set to ``WARNING``. For debugging, consider setting the log
level to ``INFO`` or ``DEBUG``.

=================
NLTK Dependencies
=================

The `NLTK <https://www.nltk.org/>`_ library is used for word and sentence tokenziation and
part of speech (POS) tagging. Tokenization and POS tagging help to identify sections of
narrative text within a document and are used across parsing families. The ``make install``
command downloads the ``punkt`` and ``averaged_perceptron_tagger`` depdenencies from ``nltk``.
If they are not already installed, you can install them with ``make install-nltk``.

======================
XML/HTML Depenedencies
======================

For XML and HTML parsing, you'll need ``libxml2`` and ``libxlst`` installed. On a Mac, you can do
that with:


.. code:: console

		$ brew install libxml2
		$ brew install libxslt

========================
Huggingface Dependencies
========================

The ``transformers`` requires the Rust compiler to be present on your system in
order to properly ``pip`` install. If a Rust compiler is not available on your system,
you can run the following command to install it:

.. code:: console

    $ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

Additionally, some tokenizers in the ``transformers`` library required the ``sentencepiece``
library. This is not included as an ``unstructured`` dependency because it only applies
to some tokenizers. See the
`sentencepiece install instructions <https://github.com/google/sentencepiece#installation>`_ for
information on how to install ``sentencepiece`` if your tokenizer requires it.
