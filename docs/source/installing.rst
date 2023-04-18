Installation
============

Quick Start
-----------

Use the following instructions to get up and running with ``unstructured`` and test your
installation.

* Install the Python SDK with ``"pip install unstructured[local-inference]"``
	* If you do not need to process PDFs or images, you can run ``pip install unstructured``

* Install the following system dependencies if they are not already available on your system. Depending on what document types you're parsing, you may not need all of these.
	* ``libmagic-dev`` (filetype detection)
	* ``poppler-utils`` (images and PDFs)
	* ``tesseract-ocr`` (images and PDFs)
	* ``libreoffice`` (MS Office docs)
	* ``pandocs`` (EPUBs)

* If you are parsing PDFs, run the following to install the ``detectron2`` model, which ``unstructured`` uses for layout detection:
	* ``pip install "detectron2@git+https://github.com/facebookresearch/detectron2.git@e2ce8dc#egg=detectron2"``

At this point, you should be able to run the following code:

.. code:: python

  from unstructured.partition.auto import partition

  elements = partition(filename="example-docs/fake-email.eml")

And if you installed with `local-inference`, you should be able to run this as well:

.. code:: python

  from unstructured.partition.auto import partition

  elements = partition("example-docs/layout-parser-paper.pdf")


Installation with ``conda`` on Windows
--------------------------------------

You can install and run ``unstructured`` on Windows with ``conda``, but the process
involves a few extra steps. This section will help you get up and running.

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
does not officially support Windows, but it is possible to get it to install on Windows.
The installation instructions are based on the instructions LayoutParser provides
`here <https://layout-parser.github.io/tutorials/installation#for-windows-users>`_.

* Run ``pip install pycocotools-windows`` to install a Windows compatible version of ``pycocotools``. Alternatively, you can run ``pip3 install "git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI"`` as outlined in `this GitHub issue <https://github.com/cocodataset/cocoapi/issues/169#issuecomment-462528628>`_.
* Run ``git clone https://github.com/ivanpp/detectron2.git``, then ``cd detectron2``, then ``pip install -e .`` to install a Windows compatible version of the ``detectron2`` library.
* Install the a Windows compatible version of ``iopath`` using the instructions outlined in `this GitHub issue <https://github.com/Layout-Parser/layout-parser/issues/15#issuecomment-819546751>`_. First, run ``git clone https://github.com/facebookresearch/iopath --single-branch --branch v0.1.8``. Then on line 753 in ``iopath/iopath/common/file_io.py`` change ``filename = path.split("/")[-1]`` to ``filename = parsed_url.path.split("/")[-1]``. After that, navigate to the ``iopath`` directory and run ``pip install -e .``.
* Run ``pip install unstructured[local-inference]``. This will install the ``unstructured_inference`` dependency.

At this point, you can verify the installation by running the following from the root directory of the ``unstructured`` `repo <https://github.com/Unstructured-IO/unstructured>`_:


.. code:: python

	from unstructured.partition.pdf import partition_pdf

	partition_pdf("example-docs/layout-parser-paper-fast.pdf", url=None)


====================
Installing PaddleOCR
====================

PaddleOCR is another package that is helpful to use in conjunction with ``unstructured``.
You can use the following steps to install ``paddleocr`` in your ``unstructured`` ``conda``
environment.

* Run ``conda install -c esri paddleocr``
* If you have the Windows version of ``detectron2`` cloned and installed locally, change the name of ``detectron2/tools`` to ``detectron2/detectron2_tools``. Otherwise, you will hit the module name conflict error described in `this issue <https://github.com/PaddlePaddle/PaddleOCR/issues/1024>`_.
* Set the environment variable ``KMP_DUPLICATE_LIB_OK`` to ``"TRUE"``. This prevents the ``libiomp5md.dll`` linking issue described `in this issue on GitHub <https://github.com/PaddlePaddle/PaddleOCR/issues/4613>`_.


At this point, you can verify the installation using the following commands. Choose a
``.jpg`` image that contains text.

.. code:: python

	import numpy as np
	from PIL import Image
	from paddleocr import PaddleOCR

	filename = "path/to/my/image.jpg"
	img = np.array(Image.open(filename))
	ocr = PaddleOCR(lang="en", use_gpu=False, show_log=False)
	result = ocr.ocr(img=img)



Logging
-------

You can set the logging level for the package with the ``LOG_LEVEL`` environment variable.
By default, the log level is set to ``WARNING``. For debugging, consider setting the log
level to ``INFO`` or ``DEBUG``.


Extra Dependencies
-------------------

==================
Filetype Detection
==================

The ``filetype`` module in ``unstructured`` uses ``libmagic`` to detect MIME types. For
this to work, you'll need ``libmagic`` installed on your computer. On a Mac, you can run:

.. code:: console

		$ brew install libmagic

One Debian, run:

.. code:: console

		$ sudo apt-get install -y libmagic-dev


If you are on Windows using ``conda``, run:

.. code:: console

		$ conda install -c conda-forge libmagic

======================
XML/HTML Dependencies
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
