Bricks
======

The goal of this page is to introduce you to the concept of bricks.
Bricks are functions that live in ``unstructured`` and are the primary public API for the library.
There are three types of bricks in ``unstructured``, corresponding to the different stages of document pre-processing: partitioning, cleaning, and staging.
After reading this section, you should understand the following:

* How to extract content from a document using partitioning bricks.
* How to remove unwanted content from document elements using cleaning bricks.
* How to prepare data for downstream use cases using staging bricks



############
Partitioning
############


Partitioning bricks in ``unstructured`` allow users to extract structured content from a raw unstructured document.
These functions break a document down into elements such as ``Title``, ``NarrativeText``, and ``ListItem``,
enabling users to decide what content they'd like to keep for their particular application.
If you're training a summarization model, for example, you may only be interested in ``NarrativeText``.


The easiest way to partition documents in unstructured is to use the ``partition`` brick.
If you call the ``partition`` brick, ``unstructured`` will use ``libmagic`` to automatically determine the file type and invoke the appropriate partition function.
In cases where ``libmagic`` is not available, filetype detection will fall back to using the file extension.

As shown in the examples below, the ``partition`` function accepts both filenames and file-like objects as input.
``partition`` also has some optional kwargs.
For example, if you set ``include_page_breaks=True``, the output will include ``PageBreak`` elements if the filetype supports it.
Additionally you can bypass the filetype detection logic with the optional  ``content_type`` argument which may be specified with either the ``filename`` or file-like object, ``file``.
You can find a full listing of optional kwargs in the documentation below.

.. code:: python

  from unstructured.partition.auto import partition


  filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
  elements = partition(filename=filename, content_type="application/pdf")
  print("\n\n".join([str(el) for el in elements][:10]))


.. code:: python

  from unstructured.partition.auto import partition


  filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
  with open(filename, "rb") as f:
    elements = partition(file=f, include_page_breaks=True)
  print("\n\n".join([str(el) for el in elements][5:15]))


The ``unstructured`` library also includes partitioning bricks targeted at specific document types.
The ``partition`` brick uses these document-specific partitioning bricks under the hood.
There are a few reasons you may want to use a document-specific partitioning brick instead of ``partition``:

* If you already know the document type, filetype detection is unnecessary. Using the document-specific brick directly, or passing in the ``content_type`` will make your program run faster.
* Fewer dependencies. You don't need to install ``libmagic`` for filetype detection if you're only using document-specific bricks.
* Additional features. The API for partition is the least common denominator for all document types. Certain document-specific brick include extra features that you may want to take advantage of. For example, ``partition_html`` allows you to pass in a URL so you don't have to store the ``.html`` file locally. See the documentation below learn about the options available in each partitioning brick.


Below we see an example of how to partition a document directly with the URL using the partition_html function.

.. code:: python

  from unstructured.partition.html import partition_html

  url = "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-philadelphia-eagles-spt-intl/index.html"
  elements = partition_html(url=url)
  print("\n\n".join([str(el) for el in elements]))


``partition``
--------------

The ``partition`` brick is the simplest way to partition a document in ``unstructured``.
If you call the ``partition`` function, ``unstructured`` will attempt to detect the
file type and route it to the appropriate partitioning brick. All partitioning bricks
called within ``partition`` are called using the default kwargs. Use the document-type
specific bricks if you need to apply non-default settings.
``partition`` currently supports ``.docx``, ``.doc``, ``.odt``, ``.pptx``, ``.ppt``, ``.xlsx``, ``.csv``, ``.tsv``, ``.eml``, ``.msg``, ``.rtf``, ``.epub``, ``.html``, ``.xml``, ``.pdf``,
``.png``, ``.jpg``, and ``.txt`` files.
If you set the ``include_page_breaks`` kwarg to ``True``, the output will include page breaks. This is only supported for ``.pptx``, ``.html``, ``.pdf``,
``.png``, and ``.jpg``.
The ``strategy`` kwarg controls the strategy for partitioning documents. Generally available strategies are `"fast"` for
faster processing and `"hi_res"` for more accurate processing.


.. code:: python

  import docx

  from unstructured.partition.auto import partition

  document = docx.Document()
  document.add_paragraph("Important Analysis", style="Heading 1")
  document.add_paragraph("Here is my first thought.", style="Body Text")
  document.add_paragraph("Here is my second thought.", style="Normal")
  document.save("mydoc.docx")

  elements = partition(filename="mydoc.docx")

  with open("mydoc.docx", "rb") as f:
      elements = partition(file=f)


.. code:: python

  from unstructured.partition.auto import partition

  elements = partition(filename="example-docs/layout-parser-paper-fast.pdf")


The ``partition`` function also accepts a ``url`` kwarg for remotely hosted documents. If you want
to force ``partition`` to treat the document as a particular MIME type, use the ``content_type``
kwarg in conjunction with ``url``. Otherwise, ``partition`` will use the information from
the ``Content-Type`` header in the HTTP response. The ``ssl_verify`` kwarg controls whether
or not SSL verification is enabled for the HTTP request. By default it is on. Use ``ssl_verify=False``
to disable SSL verification in the request.


.. code:: python

  from unstructured.partition.auto import partition

  url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"
  elements = partition(url=url)
  elements = partition(url=url, content_type="text/markdown")

For more information about the ``partition`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/auto.py>`_.


``partition_csv``
------------------

The ``partition_csv`` function pre-processes CSV files. The output is a single
``Table`` element. The ``text_as_html`` attribute in the element metadata will
contain an HTML representation of the table.

Examples:

.. code:: python

  from unstructured.partition.csv import partition_csv

  elements = partition_csv(filename="example-docs/stanley-cups.csv")
  print(elements[0].metadata.text_as_html)

For more information about the ``partition_csv`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/csv.py>`_.


``partition_doc``
------------------

The ``partition_doc`` partitioning brick pre-processes Microsoft Word documents
saved in the ``.doc`` format. This partition brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_doc`` can take a filename or file-like object
as input.
``partiton_doc`` uses ``libreoffice`` to convert the file to ``.docx`` and then
calls ``partition_docx``. Ensure you have ``libreoffice`` installed
before using ``partition_doc``.

Examples:

.. code:: python

  from unstructured.partition.doc import partition_doc

  elements = partition_doc(filename="example-docs/fake.doc")

For more information about the ``partition_doc`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/doc.py>`_.


``partition_docx``
------------------

The ``partition_docx`` partitioning brick pre-processes Microsoft Word documents
saved in the ``.docx`` format. This partition brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_docx`` can take a filename or file-like object
as input, as shown in the two examples below.

Examples:

.. code:: python

  import docx

  from unstructured.partition.docx import partition_docx

  document = docx.Document()
  document.add_paragraph("Important Analysis", style="Heading 1")
  document.add_paragraph("Here is my first thought.", style="Body Text")
  document.add_paragraph("Here is my second thought.", style="Normal")
  document.save("mydoc.docx")

  elements = partition_docx(filename="mydoc.docx")

  with open("mydoc.docx", "rb") as f:
      elements = partition_docx(file=f)

In Word documents, headers and footers are specified per section. In the output,
the ``Header`` elements will appear at the beginning of a section and ``Footer``
elements will appear at the end. MSFT Word headers and footers have a ``header_footer_type``
metadata field indicating where the header or footer applies. Valid values are
``"primary"``, ``"first_page"`` and ``"even_page"``.

``partition_docx`` will include page numbers in the document metadata when page breaks
are present in the document. The function will detect user inserted page breaks
and page breaks inserted by the Word document renderer. Some (but not all) Word document renderers
insert page breaks when you save the document. If your Word document renderer does not do that,
you may not see page numbers in the output even if you see them visually when you open the
document. If that is the case, you can try saving the document with a different renderer.

For more information about the ``partition_docx`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/docx.py>`_.


``partition_email``
---------------------

The ``partition_email`` function partitions ``.eml`` documents and works with exports
from email clients such as Microsoft Outlook and Gmail. The ``partition_email``
takes a filename, file-like object, or raw text as input and produces a list of
document ``Element`` objects as output. Also ``content_source`` can be set to ``text/html``
(default) or ``text/plain`` to process the html or plain text version of the email, respectively.
In order for ``partition_email`` to also return the header information (e.g. sender, recipient,
attachment, etc.), ``include_headers`` must be set to ``True``. Returns tuple with body elements
first and header elements second, if ``include_headers`` is True.

Examples:

.. code:: python

  from unstructured.partition.email import partition_email

  elements = partition_email(filename="example-docs/fake-email.eml")

  with open("example-docs/fake-email.eml", "r") as f:
      elements = partition_email(file=f)

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text)

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text, content_source="text/plain")

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text, include_headers=True)


``partition_email`` includes a ``max_partition`` parameter that indicates the maximum character
length for a document element.
This parameter only applies if ``"text/plain"`` is selected as the ``content_source``.
The default value is ``1500``, which roughly corresponds to
the average character length for a paragraph.
You can disable ``max_partition`` by setting it to ``None``.


You can optionally partition e-mail attachments by setting ``process_attachments=True``.
If you set ``process_attachments=True``, you'll also need to pass in a partitioning
function to ``attachment_partitioner``. The following is an example of what the
workflow looks like:

.. code:: python

  from unstructured.partition.auto import partition
  from unstructured.partition.email import partition_email

  filename = "example-docs/eml/fake-email-attachment.eml"
  elements = partition_email(
    filename=filename, process_attachments=True, attachment_partitioner=partition
  )

For more information about the ``partition_email`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/email.py>`_.


``partition_epub``
---------------------

The ``partition_epub`` function processes e-books in EPUB3 format. The function
first converts the document to HTML using ``pandocs`` and then calls ``partition_html``.
You'll need `pandocs <https://pandoc.org/installing.html>`_ installed on your system
to use ``partition_epub``.


Examples:

.. code:: python

  from unstructured.partition.epub import partition_epub

  elements = partition_epub(filename="example-docs/winter-sports.epub")

For more information about the ``partition_epub`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/epub.py>`_.


``partition_html``
---------------------

The ``partition_html`` function partitions an HTML document and returns a list
of document ``Element`` objects. ``partition_html`` can take a filename, file-like
object, string, or url as input.

The following three invocations of partition_html() are essentially equivalent:


.. code:: python

  from unstructured.partition.html import partition_html

  elements = partition_html(filename="example-docs/example-10k.html")

  with open("example-docs/example-10k.html", "r") as f:
      elements = partition_html(file=f)

  with open("example-docs/example-10k.html", "r") as f:
      text = f.read()
  elements = partition_html(text=text)



The following illustrates fetching a url and partitioning the response content.
The ``ssl_verify`` kwarg controls whether
or not SSL verification is enabled for the HTTP request. By default it is on. Use ``ssl_verify=False``
to disable SSL verification in the request.

.. code:: python

  from unstructured.partition.html import partition_html

  elements = partition_html(url="https://python.org/")

  # you can also provide custom headers:

  elements = partition_html(url="https://python.org/",
                            headers={"User-Agent": "YourScriptName/1.0 ..."})

  # and turn off SSL verification

  elements = partition_html(url="https://python.org/", ssl_verify=False)



If you website contains news articles, it can be helpful to only grab content that appears in
between the ``<article>`` tags, if the site uses that convention.
To activate this behavior, you can set ``html_assemble_articles=True``.
If ``html_assemble_articles`` is ``True``, each ``<article>`` tag will be treated as a a page.
If ``html_assemble_articles`` is ``True`` and no ``<article>`` tags are present, the behavior
is the same as ``html_assemble_articles=False``.

For more information about the ``partition_html`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/html.py>`_.


``partition_image``
---------------------

The ``partition_image`` function has the same API as ``partition_pdf``, which is document above.
The only difference is that ``partition_image`` does not need to convert a PDF to an image
prior to processing. The ``partition_image`` function supports ``.png`` and ``.jpg`` files.

You can also specify what languages to use for OCR with the ``ocr_languages`` kwarg. For example,
use ``ocr_languages="eng+deu"`` to use the English and German language packs. See the
`Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and
install instructions.


Examples:

.. code:: python

  from unstructured.partition.image import partition_image

  # Returns a List[Element] present in the pages of the parsed image document
  elements = partition_image("example-docs/layout-parser-paper-fast.jpg")

  # Applies the English and Swedish language pack for ocr
  elements = partition_image("example-docs/layout-parser-paper-fast.jpg", ocr_languages="eng+swe")


The ``strategy`` kwarg controls the method that will be used to process the PDF.
The available strategies for images are ``"auto"``, ``"hi_res"`` and ``"ocr_only"``.

The ``"auto"`` strategy will choose the partitioning strategy based on document characteristics and the function kwargs.
If ``infer_table_structure`` is passed, the strategy will be ``"hi_res"`` because that is the only strategy that
currently extracts tables for PDFs. Otherwise, ``"auto"`` will choose ``ocr_only``. ``"auto"`` is the default strategy.

The ``"hi_res"`` strategy will identify the layout of the document using ``detectron2``. The advantage of `"hi_res"` is that it
uses the document layout to gain additional information about document elements. We recommend using this strategy
if your use case is highly sensitive to correct classifications for document elements. If ``detectron2`` is not available,
the ``"hi_res"`` strategy will fall back to the ``"ocr_only"`` strategy.

The ``"ocr_only"`` strategy runs the document through Tesseract for OCR and then runs the raw text through ``partition_text``.
Currently, ``"hi_res"`` has difficulty ordering elements for documents with multiple columns. If you have a document with
multiple columns that does not have extractable text, we recoomend using the ``"ocr_only"`` strategy.

It is helpful to use ``"ocr_only"`` instead of ``"hi_res"``
if ``detectron2`` does not detect a text element in the image. To run example below, ensure you
have the Korean language pack for Tesseract installed on your system.


.. code:: python

  from unstructured.partition.image import partition_image

  filename = "example-docs/english-and-korean.png"
  elements = partition_image(filename=filename, ocr_languages="eng+kor", strategy="ocr_only")

For more information about the ``partition_image`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/image.py>`_.


``partition_md``
---------------------

The ``partition_md`` function provides the ability to parse markdown files. The
following workflow shows how to use ``partition_md``.


Examples:

.. code:: python

  from unstructured.partition.md import partition_md

  elements = partition_md(filename="README.md")

For more information about the ``partition_md`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/md.py>`_.


``partition_msg``
-----------------

The ``partition_msg`` functions processes ``.msg`` files, which is a filetype specific
to email exports from Microsoft Outlook.

Examples:

.. code:: python

  from unstructured.partition.msg import partition_msg

  elements = partition_msg(filename="example-docs/fake-email.msg")

``partition_msg`` includes a ``max_partition`` parameter that indicates the maximum character
length for a document element.
This parameter only applies if ``"text/plain"`` is selected as the ``content_source``.
The default value is ``1500``, which roughly corresponds to
the average character length for a paragraph.
You can disable ``max_partition`` by setting it to ``None``.


You can optionally partition e-mail attachments by setting ``process_attachments=True``.
If you set ``process_attachments=True``, you'll also need to pass in a partitioning
function to ``attachment_partitioner``. The following is an example of what the
workflow looks like:

.. code:: python

  from unstructured.partition.auto import partition
  from unstructured.partition.msg import partition_msg

  filename = "example-docs/fake-email-attachment.msg"
  elements = partition_msg(
    filename=filename, process_attachments=True, attachment_partitioner=partition
  )

For more information about the ``partition_msg`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/msg.py>`_.


``partition_multiple_via_api``
------------------------------

``partition_multiple_via_api`` is similar to ``partition_via_api``, but allows you to partition
multiple documents in a single REST API call. The result has the type ``List[List[Element]]``,
for example:

.. code:: python

  [
    [NarrativeText("Narrative!"), Title("Title!")],
    [NarrativeText("Narrative!"), Title("Title!")]
  ]

Examples:

.. code:: python

  from unstructured.partition.api import partition_multiple_via_api

  filenames = ["example-docs/fake-email.eml", "example-docs/fake.docx"]

  documents = partition_multiple_via_api(filenames=filenames)


.. code:: python

  from contextlib import ExitStack

  from unstructured.partition.api import partition_multiple_via_api

  filenames = ["example-docs/fake-email.eml", "example-docs/fake.docx"]
  files = [open(filename, "rb") for filename in filenames]

  with ExitStack() as stack:
      files = [stack.enter_context(open(filename, "rb")) for filename in filenames]
      documents = partition_multiple_via_api(files=files, file_filenames=filenames)

For more information about the ``partition_multiple_via_api`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/api.py>`_.


``partition_odt``
------------------

The ``partition_odt`` partitioning brick pre-processes Open Office documents
saved in the ``.odt`` format. The function first converts the document
to ``.docx`` using ``pandoc`` and then processes it using ``partition_docx``.

Examples:

.. code:: python

  from unstructured.partition.odt import partition_odt

  elements = partition_odt(filename="example-docs/fake.odt")

For more information about the ``partition_odt`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/odt.py>`_.


``partition_org``
---------------------

The ``partition_org`` function processes Org Mode (``.org``) documents. The function
first converts the document to HTML using ``pandoc`` and then calls ``partition_html``.
You'll need `pandoc <https://pandoc.org/installing.html>`_ installed on your system
to use ``partition_org``.


Examples:

.. code:: python

  from unstructured.partition.org import partition_org

  elements = partition_org(filename="example-docs/README.org")

For more information about the ``partition_org`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/org.py>`_.


``partition_pdf``
---------------------

The ``partition_pdf`` function segments a PDF document by using a document image analysis model.
If you set ``url=None``, the document image analysis model will execute locally. You need to install ``unstructured[local-inference]``
if you'd like to run inference locally.
If you set the URL, ``partition_pdf`` will make a call to a remote inference server.
``partition_pdf`` also includes a ``token`` function that allows you to pass in an authentication
token for a remote API call.

You can also specify what languages to use for OCR with the ``ocr_languages`` kwarg. For example,
use ``ocr_languages="eng+deu"`` to use the English and German language packs. See the
`Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and
install instructions. OCR is only applied if the text is not already available in the PDF document.

Examples:

.. code:: python

  from unstructured.partition.pdf import partition_pdf

  # Returns a List[Element] present in the pages of the parsed pdf document
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf")

  # Applies the English and Swedish language pack for ocr. OCR is only applied
  # if the text is not available in the PDF.
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf", ocr_languages="eng+swe")


The ``strategy`` kwarg controls the method that will be used to process the PDF.
The available strategies for PDFs are ``"auto"``, ``"hi_res"``, ``"ocr_only"``, and ``"fast"``.

The ``"auto"`` strategy will choose the partitioning strategy based on document characteristics and the function kwargs.
If ``infer_table_structure`` is passed, the strategy will be ``"hi_res"`` because that is the only strategy that
currently extracts tables for PDFs. Otherwise, ``"auto"`` will choose ``"fast"`` if the PDF text is extractable and
``"ocr_only"`` otherwise. ``"auto"`` is the default strategy.

The ``"hi_res"`` strategy will identify the layout of the document using ``detectron2``. The advantage of `"hi_res"` is that
it uses the document layout to gain additional information about document elements. We recommend using this strategy
if your use case is highly sensitive to correct classifications for document elements. If ``detectron2`` is not available,
the ``"hi_res"`` strategy will fall back to the ``"ocr_only"`` strategy.

The ``"ocr_only"`` strategy runs the document through Tesseract for OCR and then runs the raw text through ``partition_text``.
Currently, ``"hi_res"`` has difficulty ordering elements for documents with multiple columns. If you have a document with
multiple columns that does not have extractable text, we recommend using the ``"ocr_only"`` strategy. ``"ocr_only"`` falls
back to ``"fast"`` if Tesseract is not available and the document has extractable text.

The ``"fast"`` strategy will extract the text using ``pdfminer`` and process the raw text with ``partition_text``.
If the PDF text is not extractable, ``partition_pdf`` will fall back to ``"ocr_only"``. We recommend using the
``"fast"`` strategy in most cases where the PDF has extractable text.

If a PDF is copy protected, ``partition_pdf`` can process the document with the ``"hi_res"`` strategy (which
will treat it like an image), but cannot process the document with the ``"fast"`` strategy.
If the user chooses ``"fast"`` on a copy protected PDF, ``partition_pdf`` will fall back to the ``"hi_res"``
strategy. If ``detectron2`` is not installed, ``partition_pdf`` will fail for copy protected
PDFs because the document will not be processable by any of the available methods.

Examples:

.. code:: python

  from unstructured.partition.pdf import partition_pdf

  # This will process without issue
  elements = partition_pdf("example-docs/copy-protected.pdf", strategy="hi_res")

  # This will output a warning and fall back to hi_res
  elements = partition_pdf("example-docs/copy-protected.pdf", strategy="fast")


``partition_pdf`` includes a ``max_partition`` parameter that indicates the maximum character
length for a document element.
This parameter only applies if the ``"ocr_only"`` strategy is used for partitioning.
The default value is ``1500``, which roughly corresponds to
the average character length for a paragraph.
You can disable ``max_partition`` by setting it to ``None``.

For more information about the ``partition_pdf`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/pdf.py>`_.


``partition_ppt``
---------------------

The ``partition_ppt`` partitioning brick pre-processes Microsoft PowerPoint documents
saved in the ``.ppt`` format. This partition brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_ppt`` can take a filename or file-like object.
``partition_ppt`` uses ``libreoffice`` to convert the file to ``.pptx`` and then
calls ``partition_pptx``. Ensure you have ``libreoffice`` installed
before using ``partition_ppt``.

Examples:

.. code:: python

  from unstructured.partition.ppt import partition_ppt

  elements = partition_ppt(filename="example-docs/fake-power-point.ppt")

For more information about the ``partition_ppt`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/ppt.py>`_.


``partition_pptx``
---------------------

The ``partition_pptx`` partitioning brick pre-processes Microsoft PowerPoint documents
saved in the ``.pptx`` format. This partition brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_pptx`` can take a filename or file-like object
as input, as shown in the two examples below.

Examples:

.. code:: python

  from unstructured.partition.pptx import partition_pptx

  elements = partition_pptx(filename="example-docs/fake-power-point.pptx")

  with open("example-docs/fake-power-point.pptx", "rb") as f:
      elements = partition_pptx(file=f)

For more information about the ``partition_pptx`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/pptx.py>`_.


``partition_rst``
---------------------

The ``partition_rst`` function processes ReStructured Text (``.rst``) documents. The function
first converts the document to HTML using ``pandoc`` and then calls ``partition_html``.
You'll need `pandoc <https://pandoc.org/installing.html>`_ installed on your system
to use ``partition_rst``.


Examples:

.. code:: python

  from unstructured.partition.rst import partition_rst

  elements = partition_rst(filename="example-docs/README.rst")

For more information about the ``partition_rst`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/rst.py>`_.


``partition_rtf``
---------------------

The ``partition_rtf`` function processes rich text files. The function
first converts the document to HTML using ``pandocs`` and then calls ``partition_html``.
You'll need `pandocs <https://pandoc.org/installing.html>`_ installed on your system
to use ``partition_rtf``.


Examples:

.. code:: python

  from unstructured.partition.rtf import partition_rtf

  elements = partition_rtf(filename="example-docs/fake-doc.rtf")

For more information about the ``partition_rtf`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/rtf.py>`_.


``partition_text``
---------------------

The ``partition_text`` function partitions text files. The ``partition_text``
takes a filename, file-like object, and raw text as input and produces ``Element`` objects as output.

Examples:

.. code:: python

  from unstructured.partition.text import partition_text

  elements = partition_text(filename="example-docs/fake-text.txt")

  with open("example-docs/fake-text.txt", "r") as f:
    elements = partition_text(file=f)

  with open("example-docs/fake-text.txt", "r") as f:
    text = f.read()
  elements = partition_text(text=text)

If the text has extra line breaks for formatting purposes, you can group
together the broken text using the ``paragraph_grouper`` kwarg. The
``paragraph_grouper`` kwarg is a function that accepts a string and returns
another string.

Examples:

.. code:: python

  from unstructured.partition.text import partition_text
  from unstructured.cleaners.core import group_broken_paragraphs


  text = """The big brown fox
  was walking down the lane.

  At the end of the lane, the
  fox met a bear."""

  partition_text(text=text, paragraph_grouper=group_broken_paragraphs)

``partition_text`` includes a ``max_partition`` parameter that indicates the maximum character
length for a document element.
The default value is ``1500``, which roughly corresponds to
the average character length for a paragraph.
You can disable ``max_partition`` by setting it to ``None``.

For more information about the ``partition_text`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text.py>`_.


``partition_tsv``
------------------

The ``partition_tsv`` function pre-processes TSV files. The output is a single
``Table`` element. The ``text_as_html`` attribute in the element metadata will
contain an HTML representation of the table.

Examples:

.. code:: python

  from unstructured.partition.tsv import partition_tsv

  elements = partition_tsv(filename="example-docs/stanley-cups.tsv")
  print(elements[0].metadata.text_as_html)

For more information about the ``partition_tsv`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/tsv.py>`_.


``partition_via_api``
---------------------

``partition_via_api`` allows users to partition documents using the hosted Unstructured API.
The API partitions documents using the automatic ``partition`` function.
This is helpful if you're hosting
the API yourself or running it locally through a container. You can pass in your API key
using the ``api_key`` kwarg. You can use the ``content_type`` kwarg to pass in the MIME
type for the file. If you do not explicitly pass it, the MIME type will be inferred.


.. code:: python

  from unstructured.partition.api import partition_via_api

  filename = "example-docs/eml/fake-email.eml"

  elements = partition_via_api(filename=filename, api_key="MY_API_KEY", content_type="message/rfc822")

  with open(filename, "rb") as f:
    elements = partition_via_api(file=f, file_filename=filename, api_key="MY_API_KEY")


You can pass additional settings such as ``strategy``, ``ocr_languages`` and ``encoding`` to the
API through optional kwargs. These options get added to the request body when the
API is called.
See `the API documentation <https://api.unstructured.io/general/docs>`_ for a full list of
settings supported by the API.

.. code:: python

  from unstructured.partition.api import partition_via_api

  filename = "example-docs/DA-1p.pdf"

  elements = partition_via_api(
    filename=filename, api_key=api_key, strategy="auto", pdf_infer_table_structure="true"
  )

If you are self-hosting or running the API locally, you can use the ``api_url`` kwarg
to point the ``partition_via_api`` function at your self-hosted or local API.
See `here <https://github.com/Unstructured-IO/unstructured-api#dizzy-instructions-for-using-the-docker-image>`_ for
documentation on how to run the API as a container locally.


.. code:: python

  from unstructured.partition.api import partition_via_api

  filename = "example-docs/eml/fake-email.eml"

  elements = partition_via_api(
    filename=filename, api_url="http://localhost:5000/general/v0/general"
  )

For more information about the ``partition_via_api`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/api.py>`_.


``partition_xlsx``
------------------

The ``partition_xlsx`` function pre-processes Microsoft Excel documents. Each
sheet in the Excel file will be stored as a ``Table`` object. The plain text
of the sheet will be the ``text`` attribute of the ``Table``. The ``text_as_html``
attribute in the element metadata will contain an HTML representation of the table.

Examples:

.. code:: python

  from unstructured.partition.xlsx import partition_xlsx

  elements = partition_xlsx(filename="example-docs/stanley-cups.xlsx")
  print(elements[0].metadata.text_as_html)

For more information about the ``partition_xlsx`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/xlsx.py>`_.


``partition_xml``
-----------------

The ``partition_xml`` function processes XML documents.
If ``xml_keep_tags=False``, the function only returns the text attributes from the tags.
You can use ``xml_path`` in conjuntion with ``xml_keep_tags=False`` to restrict the text
extraction to specific tags.
If ``xml_keep_tags=True``, the function returns tag information in addition to tag text.
``xml_keep_tags`` is ``False`` be default.


.. code:: python

  from unstructured.partition.xml import partition_xml

  elements = partition_xml(filename="example-docs/factbook.xml", xml_keep_tags=True)

  elements = partition_xml(filename="example-docs/factbook.xml", xml_keep_tags=False)

``partition_xml`` includes a ``max_partition`` parameter that indicates the maximum character length for a document element.
The default value is ``1500``, which roughly corresponds to
the average character length for a paragraph.
You can disable ``max_partition`` by setting it to ``None``.

For more information about the ``partition_xml`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/xml.py>`_.


########
Cleaning
########


As part of data preparation for an NLP model, it's common to need to clean up your data prior to passing it into the model.
If there's unwanted content in your output, for example, it could impact the quality of your NLP model.
To help with this, the ``unstructured`` library includes cleaning bricks to help users sanitize output before sending it to downstream applications.


Some cleaning bricks apply automatically.
In the example in the **Partition** section, the output ``Philadelphia Eaglesâ\x80\x99 victory`` automatically gets converted to ``Philadelphia Eagles' victory`` in ``partition_html`` using the ``replace_unicode_quotes`` cleaning brick.
You can see how that works in the code snippet below:

.. code:: python

  from unstructured.cleaners.core import replace_unicode_quotes

  replace_unicode_quotes("Philadelphia Eaglesâ\x80\x99 victory")



Document elements in ``unstructured`` include an ``apply`` method that allow you to apply the text cleaning to the document element without instantiating a new element.
The ``apply`` method expects a callable that takes a string as input and produces another string as output.
In the example below, we invoke the ``replace_unicode_quotes`` cleaning brick using the ``apply`` method.


.. code:: python

  from unstructured.documents.elements import Text

  element = Text("Philadelphia Eaglesâ\x80\x99 victory")
  element.apply(replace_unicode_quotes)
  print(element)


Since a cleaning brick is just a ``str -> str`` function, users can also easily include their own cleaning bricks for custom data preparation tasks.
In the example below, we remove citations from a section of text.


.. code:: python

  import re

  remove_citations = lambda text: re.sub("\[\d{1,3}\]", "", text)

  element = Text("[1] Geolocated combat footage has confirmed Russian gains in the Dvorichne area northwest of Svatove.")
  element.apply(remove_citations)
  print(element)


See below for a full list of cleaning bricks in the ``unstructured`` library.


``bytes_string_to_string``
---------------------------

Converts an output string that looks like a byte string to a string using the specified encoding. This
happens sometimes in ``partition_html`` when there is a character like an emoji that isn't expected
by the HTML parser. In that case, the encoded bytes get processed.

Examples:

.. code:: python

  from unstructured.cleaners.core import bytes_string_to_string

  text = "Hello ð\x9f\x98\x80"
  # The output should be "Hello 😀"
  bytes_string_to_string(text, encoding="utf-8")


.. code:: python

  from unstructured.cleaners.core import bytes_string_to_string
  from unstructured.partition.html import partition_html

  text = """\n<html charset="utf-8"><p>Hello 😀</p></html>"""
  elements = partition_html(text=text)
  elements[0].apply(bytes_string_to_string)
  # The output should be "Hello 😀"
  elements[0].text

For more information about the ``bytes_string_to_string`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean``
---------

Cleans a section of text with options including removing bullets, extra whitespace, dashes
and trailing punctuation. Optionally, you can choose to lowercase the output.

Options:

* Applies ``clean_bullets`` if ``bullets=True``.
* Applies ``clean_extra_whitespace`` if ``extra_whitespace=True``.
* Applies ``clean_dashes`` if ``dashes=True``.
* Applies ``clean_trailing_punctuation`` if ``trailing_punctuation=True``.
* Lowercases the output if ``lowercase=True``.


Examples:

.. code:: python

  from unstructured.cleaners.core import clean

  # Returns "an excellent point!"
  clean("● An excellent point!", bullets=True, lowercase=True)

  # Returns "ITEM 1A: RISK FACTORS"
  clean("ITEM 1A:     RISK-FACTORS", extra_whitespace=True, dashes=True)

For more information about the ``clean`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_bullets``
-----------------

Removes bullets from the beginning of text. Bullets that do not appear at the beginning of the
text are not removed.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_bullets

  # Returns "An excellent point!"
  clean_bullets("● An excellent point!")

  # Returns "I love Morse Code! ●●●"
  clean_bullets("I love Morse Code! ●●●")

For more information about the ``clean_bullets`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_dashes``
----------------

Removes dashes from a section of text. Also handles special characters
such as ``\u2013``.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_dashes

  # Returns "ITEM 1A: RISK FACTORS"
  clean_dashes("ITEM 1A: RISK-FACTORS\u2013")

For more information about the ``clean_dashes`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_extra_whitespace``
--------------------------

Removes extra whitespace from a section of text. Also handles special characters
such as ``\xa0`` and newlines.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_extra_whitespace

  # Returns "ITEM 1A: RISK FACTORS"
  clean_extra_whitespace("ITEM 1A:     RISK FACTORS\n")

For more information about the ``clean_extra_whitespace`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_non_ascii_chars``
-------------------------

Removes non-ascii characters from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_non_ascii_chars

  text = "\x88This text contains®non-ascii characters!●"

  # Returns "This text containsnon-ascii characters!"
  clean_non_ascii_chars(text)

For more information about the ``clean_non_ascii_chars`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_ordered_bullets``
-------------------------

Remove alphanumeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_ordered_bullets

  # Returns "This is a very important point"
  clean_bullets("1.1 This is a very important point")

  # Returns "This is a very important point ●"
  clean_bullets("a.b This is a very important point ●")

For more information about the ``clean_ordered_bullets`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_postfix``
-----------------

Removes the postfix from a string if they match a specified pattern.

Options:

* Ignores case if ``ignore_case`` is set to ``True``. The default is ``False``.
* Strips trailing whitespace is ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.core import clean_postfix

  text = "The end! END"

  # Returns "The end!"
  clean_postfix(text, r"(END|STOP)", ignore_case=True)

For more information about the ``clean_postfix`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_prefix``
----------------

Removes the prefix from a string if they match a specified pattern.

Options:

* Ignores case if ``ignore_case`` is set to ``True``. The default is ``False``.
* Strips leading whitespace is ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.core import clean_prefix

  text = "SUMMARY: This is the best summary of all time!"

  # Returns "This is the best summary of all time!"
  clean_prefix(text, r"(SUMMARY|DESCRIPTION):", ignore_case=True)

For more information about the ``clean_prefix`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_trailing_punctuation``
-------------------------------

Removes trailing punctuation from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_trailing_punctuation

  # Returns "ITEM 1A: RISK FACTORS"
  clean_trailing_punctuation("ITEM 1A: RISK FACTORS.")

For more information about the ``clean_trailing_punctuation`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``extract_datetimetz``
----------------------

Extracts the date, time, and timezone in the ``Received`` field(s) from an ``.eml``
file. ``extract_datetimetz`` takes in a string and returns a datetime.datetime
object from the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_datetimetz

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns datetime.datetime(2021, 3, 26, 11, 4, 9, tzinfo=datetime.timezone(datetime.timedelta(seconds=43200)))
  extract_datetimetz(text)

For more information about the ``extract_datetimetz`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_email_address``
--------------------------

Extracts email addresses from a string input and returns a list of all the email
addresses in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_email_address

  text = """Me me@email.com and You <You@email.com>
      ([ba23::58b5:2236:45g2:88h2]) (10.0.2.01)"""

  # Returns "['me@email.com', 'you@email.com']"
  extract_email_address(text)

For more information about the ``extract_email_address`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_ip_address``
------------------------

Extracts IPv4 and IPv6 IP addresses in the input string and
returns a list of all IP address in input string.

.. code:: python

  from unstructured.cleaners.extract import extract_ip_address

  text = """Me me@email.com and You <You@email.com>
    ([ba23::58b5:2236:45g2:88h2]) (10.0.2.01)"""

  # Returns "['ba23::58b5:2236:45g2:88h2', '10.0.2.01']"
  extract_ip_address(text)

For more information about the ``extract_ip_address`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_ip_address_name``
----------------------------

Extracts the names of each IP address in the ``Received`` field(s) from an ``.eml``
file. ``extract_ip_address_name`` takes in a string and returns a list of all
IP addresses in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_ip_address_name

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns "['ABC.DEF.local', 'ABC.DEF.local2']"
  extract_ip_address_name(text)

For more information about the ``extract_ip_address_name`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_mapi_id``
----------------------

Extracts the ``mapi id`` in the ``Received`` field(s) from an ``.eml``
file. ``extract_mapi_id`` takes in a string and returns a list of a string
containing the ``mapi id`` in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_mapi_id

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns "['32.88.5467.123']"
  extract_mapi_id(text)

For more information about the ``extract_mapi_id`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_ordered_bullets``
---------------------------

Extracts alphanumeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_ordered_bullets

  # Returns ("1", "1", None)
  extract_ordered_bullets("1.1 This is a very important point")

  # Returns ("a", "1", None)
  extract_ordered_bullets("a.1 This is a very important point")

For more information about the ``extract_ordered_bullets`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_text_after``
----------------------

Extracts text that occurs after the specified pattern.

Options:

* If ``index`` is set, extract after the ``(index + 1)``\th occurrence of the pattern. The default is ``0``.
* Strips trailing whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_after

  text = "SPEAKER 1: Look at me, I'm flying!"

  # Returns "Look at me, I'm flying!"
  extract_text_after(text, r"SPEAKER \d{1}:")

For more information about the ``extract_text_after`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_text_before``
-----------------------

Extracts text that occurs before the specified pattern.

Options:

* If ``index`` is set, extract before the ``(index + 1)``\th occurrence of the pattern. The default is ``0``.
* Strips leading whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_before

  text = "Here I am! STOP Look at me! STOP I'm flying! STOP"

  # Returns "Here I am!"
  extract_text_before(text, r"STOP")

For more information about the ``extract_text_before`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``extract_us_phone_number``
---------------------------

Extracts a phone number from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_us_phone_number

  # Returns "215-867-5309"
  extract_us_phone_number("Phone number: 215-867-5309")

For more information about the ``extract_us_phone_number`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`_.


``group_broken_paragraphs``
---------------------------

Groups together paragraphs that are broken up with line breaks
for visual or formatting purposes. This is common in ``.txt`` files.
By default, ``group_broken_paragraphs`` groups together lines split
by ``\n``. You can change that behavior with the ``line_split``
kwarg. The function considers ``\n\n`` to be a paragraph break by
default. You can change that behavior with the ``paragraph_split`` kwarg.

Examples:

.. code:: python

  from unstructured.cleaners.core import group_broken_paragraphs

  text = """The big brown fox
  was walking down the lane.

  At the end of the lane, the
  fox met a bear."""

  group_broken_paragraphs(text)

.. code:: python

  import re
  from unstructured.cleaners.core import group_broken_paragraphs

  para_split_re = re.compile(r"(\s*\n\s*){3}")

  text = """The big brown fox

  was walking down the lane.


  At the end of the lane, the

  fox met a bear."""

  group_broken_paragraphs(text, paragraph_split=para_split_re)

For more information about the ``group_broken_paragraphs`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``remove_punctuation``
--------------------------

Removes ASCII and unicode punctuation from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import remove_punctuation

  # Returns "A lovely quote"
  remove_punctuation("“A lovely quote!”")

For more information about the ``remove_punctuation`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``replace_unicode_quotes``
--------------------------

Replaces unicode quote characters such as ``\x91`` in strings.

Examples:

.. code:: python

  from unstructured.cleaners.core import replace_unicode_quotes

  # Returns "“A lovely quote!”"
  replace_unicode_characters("\x93A lovely quote!\x94")

  # Returns ""‘A lovely quote!’"
  replace_unicode_characters("\x91A lovely quote!\x92")

For more information about the ``replace_unicode_quotes`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``translate_text``
------------------

The ``translate_text`` cleaning bricks translates text between languages. ``translate_text``
uses the `Helsinki NLP MT models <https://huggingface.co/Helsinki-NLP>`_ from
``transformers`` for machine translation. Works for Russian, Chinese, Arabic, and many
other languages.

Parameters:

* ``text``: the input string to translate.
* ``source_lang``: the two letter language code for the source language of the text.
  If ``source_lang`` is not specified,
  the language will be detected using ``langdetect``.
* ``target_lang``: the two letter language code for the target language for translation.
  Defaults to ``"en"``.


Examples:

.. code:: python

  from unstructured.cleaners.translate import translate_text

  # Output is "I'm a Berliner!"
  translate_text("Ich bin ein Berliner!")

  # Output is "I can also translate Russian!"
  translate_text("Я тоже можно переводать русский язык!", "ru", "en")

For more information about the ``translate_text`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/translate.py>`_.


#######
Staging
#######

Staging bricks in the ``unstructured`` package help prepare your data for ingestion into downstream systems.
A staging brick accepts a list of document elements as input and return an appropriately formatted dictionary as output.
In the example below, we get our narrative text samples prepared for ingestion into LabelStudio using
``the stage_for_label_studio`` brick.
We can take this data and directly upload it into LabelStudio to quickly get started with an NLP labeling task.


.. code:: python

  import json
  from unstructured.staging.label_studio import stage_for_label_studio

  output = stage_for_label_studio(narrative_text)
  print(json.dumps(output[:2], indent=4))


``convert_to_csv``
----------------------

Converts outputs to the initial structured data (ISD) format as a CSV string.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.base import convert_to_csv

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  isd_csv = convert_to_csv(elements)

For more information about the ``convert_to_csv`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`_.


``convert_to_dataframe``
------------------------

Converts a list of document ``Element`` objects to a ``pandas`` dataframe. The dataframe
will have a ``text`` column with the text from the element and a ``type`` column
indicating the element type, such as ``NarrativeText`` or ``Title``.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.base import convert_to_dataframe

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  df = convert_to_dataframe(elements)

  For more information about the ``convert_to_dataframe`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`_.


``convert_to_dict``
--------------------

Converts a list of ``Element`` objects to a dictionary. This is the default format
for representing documents in ``unstructured``.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.base import convert_to_dict

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  isd = convert_to_dict(elements)

For more information about the ``convert_to_dict`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`_.


``dict_to_elements``
---------------------

Converts a dictionary of the format produced by ``convert_to_dict`` back to a list of ``Element`` objects.

Examples:

.. code:: python

  from unstructured.staging.base import dict_to_elements

  isd = [
    {"text": "My Title", "type": "Title"},
    {"text": "My Narrative", "type": "NarrativeText"}
  ]

  # elements will look like:
  # [ Title(text="My Title"), NarrativeText(text="My Narrative")]
  elements = dict_to_elements(isd)

For more information about the ``dict_to_elements`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`_.


``stage_csv_for_prodigy``
--------------------------

Formats outputs in CSV format for use with `Prodigy <https://prodi.gy/docs/api-loaders>`_. After running ``stage_csv_for_prodigy``, you can
write the results to a CSV file that is ready to be used with Prodigy.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.prodigy import stage_csv_for_prodigy

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  metadata = [{"type": "title"}, {"source": "news"}]
  prodigy_csv_data = stage_csv_for_prodigy(elements, metadata)

  # The resulting CSV file is ready to be used with Prodigy
  with open("prodigy.csv", "w") as csv_file:
      csv_file.write(prodigy_csv_data)

For more information about the ``stage_csv_for_prodigy`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/prodigy.py>`_.


``stage_for_argilla``
--------------------------

Convert a list of ``Text`` elements to an `Argilla Dataset <https://docs.argilla.io/en/latest/reference/python/python_client.html#python-ref-datasets>`_.
The type of Argilla dataset to be generated can be specified with ``argilla_task``
parameter. Valid values for ``argilla_task`` are ``"text_classification"``,
``"token_classification"``, and ``"text2text"``. If ``"token_classification"`` is selected
and ``tokens`` is not included in the optional kwargs, the ``nltk`` word tokenizer
is used by default.


Examples:

.. code:: python

  import json

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.argilla import stage_for_argilla

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  metadata = [{"type": "title"}, {"type": "text"}]

  argilla_dataset = stage_for_argilla(elements, "text_classification", metadata=metadata)

For more information about the ``stage_for_argilla`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/argilla.py>`_.


``stage_for_baseplate``
-----------------------

The ``stage_for_baseplate`` staging function prepares a list of ``Element`` objects for ingestion
into `Baseplate <https://docs.baseplate.ai/introduction>`_, an LLM backend with a spreadsheet interface.
After running the ``stage_for_baseplate`` function, you can use the
`Baseplate API <https://docs.baseplate.ai/api-reference/documents/upsert-data-rows>`_ to upload the documents
to Baseplate. The following example code shows how to use the ``stage_for_baseplate`` function.

.. code:: python

  from unstructured.documents.elements import ElementMetadata, NarrativeText, Title
  from unstructured.staging.baseplate import stage_for_baseplate

  metadata = ElementMetadata(filename="fox.epub")

  elements = [
    Title("A Wonderful Story About A Fox", metadata=metadata),
    NarrativeText(
      "A fox ran into the chicken coop and the chickens flew off!",
      metadata=metadata,
    ),
  ]

  rows = stage_for_baseplate(elements)

The output will look like:

.. code:: python

  {
        "rows": [
            {
                "data": {
                    "element_id": "ad270eefd1cc68d15f4d3e51666d4dc8",
                    "text": "A Wonderful Story About A Fox",
                    "type": "Title",
                },
                "metadata": {"filename": "fox.epub"},
            },
            {
                "data": {
                    "element_id": "8275769fdd1804f9f2b55ad3c9b0ef1b",
                    "text": "A fox ran into the chicken coop and the chickens flew off!",
                    "type": "NarrativeText",
                },
                "metadata": {"filename": "fox.epub"},
            },
        ],
    }

For more information about the ``stage_for_baseplate`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/baseplate.py>`_.


``stage_for_datasaur``
--------------------------
Formats a list of ``Text`` elements as input to token based tasks in Datasaur.

Example:

.. code:: python

  from unstructured.documents.elements import Text
  from unstructured.staging.datasaur import stage_for_datasaur

  elements  = [Text("Text1"),Text("Text2")]
  datasaur_data = stage_for_datasaur(elements)

The output is a list of dictionaries, each one with two keys:
"text" with the content of the element and
"entities" with an empty list.

You can also specify entities in the ``stage_for_datasaur`` brick. Entities
you specify in the input will be included in the entities key in the output. The list
of entities is a list of dictionaries and must have all of the keys in the example below.
The list of entities must be the same length as the list of elements. Use an empty
list for any elements that do not have any entities.

Example:

.. code:: python

  from unstructured.documents.elements import Text
  from unstructured.staging.datasaur import stage_for_datasaur

  elements  = [Text("Hi my name is Matt.")]
  entities = [[{"text": "Matt", "type": "PER", "start_idx": 11, "end_idx": 15}]]
  datasaur_data = stage_for_datasaur(elements, entities)

For more information about the ``stage_for_datasaur`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/datasaur.py>`_.


``stage_for_label_box``
--------------------------

Formats outputs for use with `LabelBox <https://docs.labelbox.com/docs/overview>`_. LabelBox accepts cloud-hosted data
and does not support importing text directly. The ``stage_for_label_box`` does the following:

* Stages the data files in the ``output_directory`` specified in function arguments to be uploaded to a cloud storage service.
* Returns a config of type ``List[Dict[str, Any]]`` that can be written to a ``json`` file and imported into LabelBox.

**Note:** ``stage_for_label_box`` does not upload the data to remote storage such as S3. Users can upload the data to S3
using ``aws s3 sync ${output_directory} ${url_prefix}`` after running the ``stage_for_label_box`` staging brick.

Examples:

The following example demonstrates generating a ``config.json`` file that can be used with LabelBox and uploading the staged data
files to an S3 bucket.

.. code:: python

  import os
  import json

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.label_box import stage_for_label_box

  # The S3 Bucket name where data files should be uploaded.
  S3_BUCKET_NAME = "labelbox-staging-bucket"

  # The S3 key prefix (I.e. directory) where data files should be stored.
  S3_BUCKET_KEY_PREFIX = "data/"

  # The URL prefix where the data files will be accessed.
  S3_URL_PREFIX = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{S3_BUCKET_KEY_PREFIX}"

  # The local output directory where the data files will be staged for uploading to a Cloud Storage service.
  LOCAL_OUTPUT_DIRECTORY = "/tmp/labelbox-staging"

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]

  labelbox_config = stage_for_label_box(
      elements,
      output_directory=LOCAL_OUTPUT_DIRECTORY,
      url_prefix=S3_URL_PREFIX,
      external_ids=["id1", "id2"],
      attachments=[[{"type": "RAW_TEXT", "value": "Title description"}], [{"type": "RAW_TEXT", "value": "Narrative Description"}]],
      create_directory=True,
  )

  # The resulting JSON config file is ready to be used with LabelBox.
  with open("config.json", "w+") as labelbox_config_file:
      json.dump(labelbox_config, labelbox_config_file, indent=4)


  # Upload staged data files to S3 from local output directory.
  def upload_staged_files():
      from s3fs import S3FileSystem
      fs = S3FileSystem()
      for filename in os.listdir(LOCAL_OUTPUT_DIRECTORY):
          filepath = os.path.join(LOCAL_OUTPUT_DIRECTORY, filename)
          upload_key = os.path.join(S3_BUCKET_KEY_PREFIX, filename)
          fs.put_file(lpath=filepath, rpath=os.path.join(S3_BUCKET_NAME, upload_key))

  upload_staged_files()

For more information about the ``stage_for_label_box`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/label_box.py>`_.


``stage_for_label_studio``
--------------------------

Formats outputs for upload to LabelStudio. After running ``stage_for_label_studio``, you can
write the results to a JSON folder that is ready to be included in a new LabelStudio project.

Examples:

.. code:: python

  import json

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.label_studio import stage_for_label_studio

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  label_studio_data = stage_for_label_studio(elements, text_field="my_text", id_field="my_id")

  # The resulting JSON file is ready to be uploaded to LabelStudio
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)


You can also include pre-annotations and predictions as part of your LabelStudio upload.

The ``annotations`` kwarg is a list of lists. If ``annotations`` is specified, there must be a list of
annotations for each element in the ``elements`` list. If an element does not have any annotations,
use an empty list.
The following shows an example of how to upload annotations for the "Text Classification"
task in LabelStudio:

.. code:: python

  import json

  from unstructured.documents.elements import NarrativeText
  from unstructured.staging.label_studio import (
      stage_for_label_studio,
      LabelStudioAnnotation,
      LabelStudioResult,
  )



  elements = [NarrativeText(text="Narrative")]
  annotations = [[
    LabelStudioAnnotation(
        result=[
            LabelStudioResult(
                type="choices",
                value={"choices": ["Positive"]},
                from_name="sentiment",
                to_name="text",
            )
        ]
    )
  ]]
  label_studio_data = stage_for_label_studio(
      elements,
      annotations=annotations,
      text_field="my_text",
      id_field="my_id"
  )

  # The resulting JSON file is ready to be uploaded to LabelStudio
  # with annotations included
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)


Similar to annotations, the ``predictions`` kwarg is also a list of lists. A ``prediction`` is an annotation with
the addition of a ``score`` value. If ``predictions`` is specified, there must be a list of
predictions for each element in the ``elements`` list. If an element does not have any predictions, use an empty list.
The following shows an example of how to upload predictions for the "Text Classification"
task in LabelStudio:

.. code:: python

  import json

  from unstructured.documents.elements import NarrativeText
  from unstructured.staging.label_studio import (
      stage_for_label_studio,
      LabelStudioPrediction,
      LabelStudioResult,
  )



  elements = [NarrativeText(text="Narrative")]
  predictions = [[
    LabelStudioPrediction(
        result=[
            LabelStudioResult(
                type="choices",
                value={"choices": ["Positive"]},
                from_name="sentiment",
                to_name="text",
            )
        ],
        score=0.68
    )
  ]]
  label_studio_data = stage_for_label_studio(
      elements,
      predictions=predictions,
      text_field="my_text",
      id_field="my_id"
  )

  # The resulting JSON file is ready to be uploaded to LabelStudio
  # with annotations included
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)


The following shows an example of how to upload annotations for the "Named Entity Recognition"
task in LabelStudio:

.. code:: python

  import json

  from unstructured.documents.elements import NarrativeText
  from unstructured.staging.label_studio import (
      stage_for_label_studio,
      LabelStudioAnnotation,
      LabelStudioResult,
  )



  elements = [NarrativeText(text="Narrative")]
  annotations = [[
    LabelStudioAnnotation(
        result=[
            LabelStudioResult(
                type="labels",
                value={"start": 0, "end": 9, "text": "Narrative", "labels": ["MISC"]},
                from_name="label",
                to_name="text",
            )
        ]
    )
  ]]
  label_studio_data = stage_for_label_studio(
      elements,
      annotations=annotations,
      text_field="my_text",
      id_field="my_id"
  )

  # The resulting JSON file is ready to be uploaded to LabelStudio
  # with annotations included
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)


See the `LabelStudio docs <https://labelstud.io/tags/labels.html>`_ for a full list of options
for labels and annotations.

For more information about the ``stage_for_label_studio`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/label_studio.py>`_.


``stage_for_prodigy``
--------------------------

Formats outputs in JSON format for use with `Prodigy <https://prodi.gy/docs/api-loaders>`_. After running ``stage_for_prodigy``, you can
write the results to a JSON file that is ready to be used with Prodigy.

Examples:

.. code:: python

  import json

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.prodigy import stage_for_prodigy

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  metadata = [{"type": "title"}, {"type": "text"}]
  prodigy_data = stage_for_prodigy(elements, metadata)

  # The resulting JSON file is ready to be used with Prodigy
  with open("prodigy.json", "w") as f:
      json.dump(prodigy_data, f, indent=4)


**Note**: Prodigy recommends ``.jsonl`` format for feeding data to API loaders. After running ``stage_for_prodigy``, you can
use the ``save_as_jsonl`` utility function to save the formatted data to a ``.jsonl`` file that is ready to be used with Prodigy.

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.prodigy import stage_for_prodigy
  from unstructured.utils import save_as_jsonl

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  metadata = [{"type": "title"}, {"type": "text"}]
  prodigy_data = stage_for_prodigy(elements, metadata)

  # The resulting jsonl file is ready to be used with Prodigy.
  save_as_jsonl(prodigy_data, "prodigy.jsonl")

For more information about the ``stage_for_prodigy`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/prodigy.py>`_.


``stage_for_transformers``
--------------------------

Prepares ``Text`` elements for processing in ``transformers`` pipelines
by splitting the elements into chunks that fit into the model's attention window.

Examples:

.. code:: python

    from transformers import AutoTokenizer, AutoModelForTokenClassification
    from transformers import pipeline

    from unstructured.documents.elements import NarrativeText
    from unstructured.staging.huggingface import stage_for_transformers

    model_name = "hf-internal-testing/tiny-bert-for-token-classification"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)

    nlp = pipeline("ner", model=model, tokenizer=tokenizer)

    text = """From frost advisories this morning to a strong cold front expected later this week, the chance of fall showing up is real.

    There's a refreshing crispness to the air, and it looks to get only more pronounced as the week goes on.

    Frost advisories were in place this morning across portions of the Appalachians and coastal Maine as temperatures dropped into the 30s.

    Temperatures this morning were in the 40s as far south as the Florida Panhandle.

    And Maine even had a few reports of their first snow of the season Sunday. More cities could see their first snow later this week.

    Yes, hello fall!

    As temperatures moderate during the next few days, much of the east will stay right around seasonal norms, but the next blast of cold air will be strong and come with the potential for hazardous conditions.

    "A more active fall weather pattern is expected to evolve by the end of this week and continuing into the weekend as a couple of cold fronts move across the central and eastern states," the Weather Prediction Center said.

    The potent cold front will come in from Canada with a punch of chilly air, heavy rain and strong wind.

    The Weather Prediction Center has a slight risk of excessive rainfall for much of the Northeast and New England on Thursday, including places like New York City, Buffalo and Burlington, so we will have to look out for flash flooding in these areas.

    "More impactful weather continues to look likely with confidence growing that our region will experience the first real fall-like system with gusty to strong winds and a period of moderate to heavy rain along and ahead of a cold front passage," the National Weather Service office in Burlington wrote.

    The potential for very heavy rain could accompany the front, bringing up to two inches of rain for much of the area, and isolated locations could see even more.

    "Ensembles [forecast models] show median rainfall totals by Wednesday night around a half inch, with a potential for some spots to see around one inch, our first substantial rainfall in at least a couple of weeks," the weather service office in Grand Rapids noted, adding, "It may also get cold enough for some snow to mix in Thursday night to Friday morning, especially in the higher terrain north of Grand Rapids toward Cadillac."

    There is also a chance for very strong winds to accompany the system.

    The weather service is forecasting winds of 30-40 mph ahead of the cold front, which could cause some tree limbs to fall and sporadic power outages.

    Behind the front, temperatures will fall.

    "East Coast, with highs about 5-15 degrees below average to close out the workweek and going into next weekend, with highs only in the 40s and 50s from the Great Lakes to the Northeast on most days," the Weather Prediction Center explained.

    By the weekend, a second cold front will drop down from Canada and bring a reinforcing shot of chilly air across the eastern half of the country."""

    elements = stage_for_transformers([NarrativeText(text=text)], tokenizer)


The following optional keyword arguments can be specified in
``stage_for_transformers``:

    * ``buffer``: Indicates the number of tokens to leave as a buffer for the attention window. This is to account for special tokens like ``[CLS]`` that can appear at the beginning or end of an input sequence.
    * ``max_input_size``: The size of the attention window for the model. If not specified, the default is the ``model_max_length`` attribute on the tokenizer object.
    * ``split_function``: The function used to split the text into chunks to consider for adding to the attention window. Splits on spaces be default.
    * ``chunk_separator``: The string used to concat adjacent chunks when reconstructing the text. Uses spaces by default.

  If you need to operate on text directly instead of ``unstructured`` ``Text``
  objects, use the ``chunk_by_attention_window`` helper function. Simply modify
  the example above to include the following:

  .. code:: python

    from unstructured.staging.huggingface import chunk_by_attention_window

    chunks = chunk_by_attention_window(text, tokenizer)

    results = [nlp(chunk) for chunk in chunks]

For more information about the ``stage_for_transformers`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/huggingface.py>`_.


``stage_for_weaviate``
-----------------------

The ``stage_for_weaviate`` staging function prepares a list of ``Element`` objects for ingestion into
the `Weaviate <https://weaviate.io/>`_ vector database. You can create a schema in Weaviate
for the `unstructured` outputs using the following workflow:

.. code:: python

  from unstructured.staging.weaviate import create_unstructured_weaviate_class

  import weaviate

  # Change `class_name` if you want the class for unstructured documents in Weaviate
  # to have a different name
  unstructured_class = create_unstructured_weaviate_class(class_name="UnstructuredDocument")
  schema = {"classes": [unstructured_class]}

  client = weaviate.Client("http://localhost:8080")
  client.schema.create(schema)


Once the schema is created, you can batch upload documents to Weaviate using the following workflow.
See the `Weaviate documentation <https://weaviate.io/developers/weaviate>`_ for more details on
options for uploading data and querying data once it has been uploaded.


.. code:: python

  from unstructured.partition.pdf import partition_pdf
  from unstructured.staging.weaviate import stage_for_weaviate

  import weaviate
  from weaviate.util import generate_uuid5


  filename = "example-docs/layout-parser-paper-fast.pdf"
  elements = partition_pdf(filename=filename, strategy="fast")
  data_objects = stage_for_weaviate(elements)

  client = weaviate.Client("http://localhost:8080")

  with client.batch(batch_size=10) as batch:
      for data_object in tqdm.tqdm(data_objects):
          batch.add_data_object(
              data_object,
              unstructured_class_name,
              uuid=generate_uuid5(data_object),
          )

For more information about the ``stage_for_weaviate`` brick, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/weaviate.py>`_.


######################
Other helper functions
######################

The ``unstructured`` library also contains other useful helpful functions to aid in processing documents.
You can see a list of the available helper functions below:


``contains_us_phone_number``
----------------------------

Checks to see if a section of text contains a US phone number.

Examples:

.. code:: python

  from unstructured.partition.text_type import contains_us_phone_number

  # Returns True because the text includes a phone number
  contains_us_phone_number("Phone number: 215-867-5309")

For more information about the ``contains_us_phone_number`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``contains_verb``
-----------------

Checks if the text contains a verb. This is used in ``is_possible_narrative_text``, but can
be used independently as well. The function identifies verbs using the NLTK part of speech
tagger. Text that is all upper case is lower cased before part of speech detection. This is
because the upper case letters sometimes cause the part of speech tagger to miss verbs.
The following part of speech tags are identified as verbs:

* ``VB``
* ``VBG``
* ``VBD``
* ``VBN``
* ``VBP``
* ``VBZ``

Examples:

.. code:: python

  from unstructured.partition.text_type import contains_verb

  # Returns True because the text contains a verb
  example_1 = "I am going to run to the store to pick up some milk."
  contains_verb(example_1)

  # Returns False because the text does not contain a verb
  example_2 = "A friendly dog"
  contains_verb(example_2)

For more information about the ``contains_verb`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``exceeds_cap_ratio``
---------------------

Determines if the section of text exceeds the specified caps ratio. Used in
``is_possible_narrative_text`` and ``is_possible_title``, but can be used independently
as well. You can set the caps threshold using the ``threshold`` kwarg. The threshold
defaults to ``0.3``. Only runs on sections of text that are a single sentence. The caps ratio check does not apply to text that is all capitalized.

Examples:

.. code:: python

  from unstructured.partition.text_type import exceeds_cap_ratio

  # Returns True because the text is more than 30% caps
  example_1 = "LOOK AT ME I AM YELLING"
  exceeds_cap_ratio(example_1)

  # Returns False because the text is less than 30% caps
  example_2 = "Look at me, I am no longer yelling"
  exceeds_cap_ratio(example_2)

  # Returns False because the text is more than 1% caps
  exceeds_cap_ratio(example_2, threshold=0.01)

For more information about the ``exceeds_cap_ratio`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``extract_attachment_info``
----------------------------

The ``extract_attachment_info`` function takes an ``email.message.Message`` object
as input and returns the a list of dictionaries containing the attachment information,
such as ``filename``, ``size``, ``payload``, etc. The attachment is saved to the ``output_dir``
if specified.

.. code:: python

  import email
  from unstructured.partition.email import extract_attachment_info

  with open("example-docs/fake-email-attachment.eml", "r") as f:
      msg = email.message_from_file(f)
  attachment_info = extract_attachment_info(msg, output_dir="example-docs")

For more information about the ``extract_attachment_info`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/email.py>`_.


``is_bulleted_text``
----------------------

Uses regular expression patterns to check if a snippet of text is a bullet point. Only
triggers if the bullet point appears at the start of the snippet.

Examples:

.. code:: python

  from unstructured.partition.text_type import is_bulleted_text

  # Returns True
  is_bulleted_text("● An excellent point!")

  # Returns False
  is_bulleted_text("I love Morse Code! ●●●")

For more information about the ``is_bulleted_text`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``is_possible_narrative_text``
------------------------------

The ``is_possible_narrative_text`` function determines if a section of text is a candidate
for consideration as narrative text. The function performs the following checks on input text:

* Empty text cannot be narrative text
* Text that is all numeric cannot be narrative text
* Text that does not contain a verb cannot be narrative text
* Narrative text must contain at least one English word (if ``language`` is set to "en")
* Text that exceeds the specified caps ratio cannot be narrative text. The threshold
  is configurable with the ``cap_threshold`` kwarg. To ignore this check, you can set
  ``cap_threshold=1.0``. You can also set the threshold by using the
  ``UNSTRUCTURED_NARRATIVE_TEXT_CAP_THRESHOLD`` environment variable. The environment variable
  takes precedence over the kwarg.
* If a the text contains too many non-alpha characters it is
  not narrative text.
  The default is to expect a minimum of 50% alpha characters
  (not countings spaces). You can change the minimum value with the
  ``non_alpha_ratio`` kwarg or the ``UNSTRUCTURED_NARRATIVE_TEXT_NON_ALPHA_RATIO`` environment variable.
  The environment variables takes precedence over the kwarg.
* The cap ratio test does not apply to text that is all uppercase.
* If you use the ``language=""`` kwarg or set the ``UNSTRUCTURED_LANGUAGE`` environment variable to ``""``, the function will skip the verb check and the English word check.
* If you use the ``language_checks=True`` kwarg or set the ``UNSTRUCTURED_LANGUAGE_CHECKS`` environment variable to ``"true"``, the function will apply language specific checks such as vocab part of speech checks.


Examples:

.. code:: python

  from unstructured.partition.text_type import is_possible_narrative_text

  # Returns True because the example passes all the checks
  example_1 = "Make sure you brush your teeth before you go to bed."
  is_possible_narrative_text(example_1)

  # Returns False because the text exceeds the caps ratio and does not contain a verb
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_narrative_text(example_2)

  # Returns True because the text has a verb and does not exceed the cap_threshold
  example_3 = "OLD MCDONALD HAD A FARM"
  is_possible_narrative_text(example_3, cap_threshold=1.0)

For more information about the ``is_possible_narrative_text`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``is_possible_title``
---------------------

The ``is_possible_title`` function determines if a section of text is a candidate
for consideration as a title. The function performs the following checks:

* Empty text cannot be a title
* Text that is all numeric cannot be a title.
* If a title contains too many words it is not a title. The default max length is ``12``. You can change the max length with
  the ``title_max_word_length`` kwarg or the ``UNSTRUCTURED_TITLE_MAX_WORD_LENGTH`` environment variable. The environment
  variable takes precedence over the kwarg.
* If a text contains too many non-alpha characters it is not a
  title. The default is to expect a minimum of 50% alpha characters
  (not countings spaces). You can change the minimum value with the
  ``non_alpha_ratio`` kwarg or the ``UNSTRUCTURED_TITLE_NON_ALPHA_RATIO`` environment variable.
  The environment variables takes precedence over the kwarg.
* Narrative text must contain at least one English word (if ``language`` is set to "en")
* If a title contains more than one sentence that exceeds a certain length, it cannot be a title. Sentence length threshold is controlled by the ``sentence_min_length`` kwarg and defaults to 5.
* If a segment of text ends in a comma, it is not considered a potential title. This is to avoid salutations like "To My Dearest Friends," getting flagged as titles.
* If you use the ``language=""`` kwarg or set the ``UNSTRUCTURED_LANGUAGE`` environment variable to ``""``, the function will skip the English word check.
* If you use the ``language_checks=True`` kwarg or set the ``UNSTRUCTURED_LANGUAGE_CHECKS`` environment variable to ``"true"``, the function will apply language specific checks such as vocab part of speech checks.




Examples:

.. code:: python

  from unstructured.partition.text_type import is_possible_title

  # Returns True because the text passes all the tests
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_title(example_2)

  # Returns True because there is only one sentence
  example_2 = "Make sure you brush your teeth before you go to bed."
  is_possible_title(example_2, sentence_min_length=5)

  # Returns False because there are two sentences
  example_3 = "Make sure you brush your teeth. Do it before you go to bed."
  is_possible_title(example_3, sentence_min_length=5)

For more information about the ``is_possible_title`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.


``sentence_count``
------------------

Counts the number of sentences in a section of text. Optionally, you can only include
sentences that exceed a specified word count. Punctuation counts as a word token
in the sentence. The function uses the NLTK sentence and word tokeniers to identify
distinct sentences and words.

Examples:

.. code:: python

  from unstructured.partition.text_type import sentence_count

  example = "Look at me! I am a document with two sentences."

  # Returns 2 because the example contains two sentences
  sentence_count(example)

  # Returns 1 because the first sentence in the example does not contain five word tokens.
  sentence_count(example, min_length=5)

For more information about the ``sentence_count`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text_type.py>`_.
