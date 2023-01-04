Installation
============

You can install the library by cloning the repo and running ``make install`` from the
root directory. Developers can run ``make install-local`` to install the dev and test
requirements alongside the base requirements. If you want a minimal installation without any
parser specific dependencies, run ``make install-base``.


Installation with ``conda`` on Windows
--------------------------------------

You can install and run ``unstructured`` on Windows with ``conda``, but the process
involves a few extra steps. This section covers will help you get up and running.

* Install `Anaconda <https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html>`_ on your Windows machine.
* Install Microsoft C++ Build Tools using the instructions in `this Stackoverflow post <https://stackoverflow.com/questions/64261546/how-to-solve-error-microsoft-visual-c-14-0-or-greater-is-required-when-inst>`_. C++ build tools are required for the ``pycocotools`` dependency.
* Run ``conda env create -f environment.yml`` using the ``environment.yml`` file in the ``unstructured`` repo to create a virtual environment. The environment will be named ``unstructured``.
* Run ``conda activate unstructured`` to activate the virtualenvironment.
* Run ``pip install unstructured`` to install the ``unstructured`` library.

===============================================
Setting up ``unstructured`` for local inference
===============================================

If you need to run model inferences locally, there are a few additional steps you need to
take. The main challenge is installing ``detectron2`` for PDF layout parsing. ``detectron2``
does not officially support Windows, but it is possible to get it install on Windows.
The installation instructions are based on the instructions LayoutParser provides
`here <https://layout-parser.github.io/tutorials/installation#for-windows-users>`_.

* Run ``pip install pycocotools-windows`` to install a Windows compatible version of ``pycocotools``. Alternatively, you can run ``pip3 install "git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI"`` as outlined in `this GitHub issues <https://github.com/cocodataset/cocoapi/issues/169#issuecomment-462528628>`_.
* Run ``git clone https://github.com/ivanpp/detectron2.git && cd detectron2 && pip install -e .`` to install a Windows compatible version of the ``detectron2`` library.
* Install the a Windows compatible version of ``iopath`` using the instructions outlined in `this GitHub issue <https://github.com/Layout-Parser/layout-parser/issues/15#issuecomment-819546751>`_. First, run ``git clone https://github.com/facebookresearch/iopath --single-branch --branch v0.1.8``. Then on line 753 in ``iopath/iopath/common/file_io.py`` change ``filename = path.split("/")[-1]`` to ``filename = parsed_url.path.split("/")[-1]``. After that, navigate to the ``iopath`` directory and run ``pip install -e .``.
* Run ``pip install unstructured[local-inference]``. This will install the ``unstructured_inference`` dependency.

At this point, you can verify the installation by running the following from the root directory of the ``unstructured-inference`` `repo <https://github.com/Unstructured-IO/unstructured-inference>`_:


.. code:: python

	from unstructured_inference.inference.layout import DocumentLayout

	layout = DocumentLayout.from_file("sample-docs/loremipsum.pdf")

	print(layout.pages[0].elements)


Logging
-------

You can set the logging level for the package with the ``LOG_LEVEL`` environment variable.
By default, the log level is set to ``WARNING``. For debugging, consider setting the log
level to ``INFO`` or ``DEBUG``.


Extra Dependencies
-------------------

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
