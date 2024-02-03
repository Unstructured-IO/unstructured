############
Partitioning
############


Partitioning functions in ``unstructured`` allow users to extract structured content from a raw unstructured document.
These functions break a document down into elements such as ``Title``, ``NarrativeText``, and ``ListItem``,
enabling users to decide what content they'd like to keep for their particular application.
If you're training a summarization model, for example, you may only be interested in ``NarrativeText``.


The easiest way to partition documents in unstructured is to use the ``partition`` function.
If you call the ``partition`` function, ``unstructured`` will use ``libmagic`` to automatically determine the file type and invoke the appropriate partition function.
In cases where ``libmagic`` is not available, filetype detection will fall back to using the file extension.

The following table shows the document types the ``unstructured`` library currently supports. ``partition`` will recognize each of these document types and route the document
to the appropriate partitioning function. If you already know your document type, you can use the partitioning function listed in the table directly.

+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Document Type                                                                                       | Partition Function             | Strategies                             | Table Support  | Options                                                                                                          |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| CSV Files (`.csv`)                                                                                  | `partition_csv`                | N/A                                    | Yes            | None                                                                                                             |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| E-mails (`.eml`)                                                                                    | `partition_eml`                | N/A                                    | No             | Encoding; Max Partition; Process Attachments                                                                     |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| E-mails (`.msg`)                                                                                    | `partition_msg`                | N/A                                    | No             | Encoding; Max Partition; Process Attachments                                                                     |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| EPubs (`.epub`)                                                                                     | `partition_epub`               | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Excel Documents (`.xlsx`/`.xls`)                                                                    | `partition_xlsx`               | N/A                                    | Yes            | None                                                                                                             |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| HTML Pages (`.html`/`.htm`)                                                                         | `partition_html`               | N/A                                    | No             | Encoding; Include Page Breaks                                                                                    |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Images (`.png`/`.jpg`/`.jpeg`/`.tiff`/`.bmp`/`.heic`)                                               | `partition_image`              | "auto", "hi_res", "ocr_only"           | Yes            | Encoding; Include Page Breaks; Infer Table Structure; OCR Languages, Strategy                                    |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Markdown (`.md`)                                                                                    | `partition_md`                 | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Org Mode (`.org`)                                                                                   | `partition_org`                | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Open Office Documents (`.odt`)                                                                      | `partition_odt`                | N/A                                    | Yes            | None                                                                                                             |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| PDFs (`.pdf`)                                                                                       | `partition_pdf`                | "auto", "fast", "hi_res", "ocr_only"   | Yes            | Encoding; Include Page Breaks; Infer Table Structure; Max Partition; OCR Languages, Strategy                     |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Plain Text (`.txt`/`.text`/`.log`)                                                                  | `partition_text`               | N/A                                    | No             | Encoding; Max Partition; Paragraph Grouper                                                                       |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| PowerPoints (`.ppt`)                                                                                | `partition_ppt`                | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| PowerPoints (`.pptx`)                                                                               | `partition_pptx`               | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| ReStructured Text (`.rst`)                                                                          | `partition_rst`                | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Rich Text Files (`.rtf`)                                                                            | `partition_rtf`                | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| TSV Files (`.tsv`)                                                                                  | `partition_tsv`                | N/A                                    | Yes            | None                                                                                                             |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Word Documents (`.doc`)                                                                             | `partition_doc`                | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Word Documents (`.docx`)                                                                            | `partition_docx`               | N/A                                    | Yes            | Include Page Breaks                                                                                              |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| XML Documents (`.xml`)                                                                              | `partition_xml`                | N/A                                    | No             | Encoding; Max Partition; XML Keep Tags                                                                           |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Code Files (`.js`/`.py`/`.java`/ `.cpp`/`.cc`/`.cxx`/`.c`/`.cs`/ `.php`/`.rb`/`.swift`/`.ts`/`.go`) | `partition_text`               | N/A                                    | No             | Encoding; Max Partition; Paragraph Grouper                                                                       |
+-----------------------------------------------------------------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+

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


The ``unstructured`` library also includes partitioning functions targeted at specific document types.
The ``partition`` function uses these document-specific partitioning functions under the hood.
There are a few reasons you may want to use a document-specific partitioning function instead of ``partition``:

* If you already know the document type, filetype detection is unnecessary. Using the document-specific function directly, or passing in the ``content_type`` will make your program run faster.
* Fewer dependencies. You don't need to install ``libmagic`` for filetype detection if you're only using document-specific functions.
* Additional features. The API for partition is the least common denominator for all document types. Certain document-specific function include extra features that you may want to take advantage of. For example, ``partition_html`` allows you to pass in a URL so you don't have to store the ``.html`` file locally. See the documentation below learn about the options available in each partitioning function.


Below we see an example of how to partition a document directly with the URL using the partition_html function.

.. code:: python

  from unstructured.partition.html import partition_html

  url = "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-philadelphia-eagles-spt-intl/index.html"
  elements = partition_html(url=url)
  print("\n\n".join([str(el) for el in elements]))


``partition``
--------------

The ``partition`` function is the simplest way to partition a document in ``unstructured``.
If you call the ``partition`` function, ``unstructured`` will attempt to detect the
file type and route it to the appropriate partitioning function. All partitioning functions
called within ``partition`` are called using the default kwargs. Use the document-type
specific functions if you need to apply non-default settings.
``partition`` currently supports ``.docx``, ``.doc``, ``.odt``, ``.pptx``, ``.ppt``, ``.xlsx``, ``.csv``, ``.tsv``, ``.eml``, ``.msg``, ``.rtf``, ``.epub``, ``.html``, ``.xml``, ``.pdf``,
``.png``, ``.jpg``, ``.heic``, and ``.txt`` files.
If you set the ``include_page_breaks`` kwarg to ``True``, the output will include page breaks. This is only supported for ``.pptx``, ``.html``, ``.pdf``,
``.png``, ``.heic``, and ``.jpg``.
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

For more information about the ``partition`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/auto.py>`__.


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

For more information about the ``partition_csv`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/csv.py>`__.


``partition_doc``
------------------

The ``partition_doc`` partitioning function pre-processes Microsoft Word documents
saved in the ``.doc`` format. This partition function uses a combination of the styling
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

For more information about the ``partition_doc`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/doc.py>`__.


``partition_docx``
------------------

The ``partition_docx`` partitioning function pre-processes Microsoft Word documents
saved in the ``.docx`` format. This partition function uses a combination of the styling
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

For more information about the ``partition_docx`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/docx.py>`__.


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

If the content of an email is PGP encrypted, ``partition_email`` will return an empty
list of elements and emit a warning indicated the email is encrypted.

For more information about the ``partition_email`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/email.py>`__.


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

For more information about the ``partition_epub`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/epub.py>`__.


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

For more information about the ``partition_html`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/html.py>`__.


``partition_image``
---------------------

The ``partition_image`` function has the same API as ``partition_pdf``, which is document above.
The only difference is that ``partition_image`` does not need to convert a PDF to an image
prior to processing. The ``partition_image`` function supports ``.png``, ``.heic``, and ``.jpg`` files.

You can also specify what languages to use for OCR with the ``languages`` kwarg. For example,
use ``languages=["eng", "deu"]`` to use the English and German language packs. See the
`Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and
install instructions.


Examples:

.. code:: python

  from unstructured.partition.image import partition_image

  # Returns a List[Element] present in the pages of the parsed image document
  elements = partition_image("example-docs/layout-parser-paper-fast.jpg")

  # Applies the English and Swedish language pack for ocr
  elements = partition_image("example-docs/layout-parser-paper-fast.jpg", languages=["eng", "swe"])


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
  elements = partition_image(filename=filename, languages=["eng", "kor"], strategy="ocr_only")

For more information about the ``partition_image`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/image.py>`__.


``partition_md``
---------------------

The ``partition_md`` function provides the ability to parse markdown files. The
following workflow shows how to use ``partition_md``.


Examples:

.. code:: python

  from unstructured.partition.md import partition_md

  elements = partition_md(filename="README.md")

For more information about the ``partition_md`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/md.py>`__.


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

If the content of an email is PGP encrypted, ``partition_msg`` will return an empty
list of elements and emit a warning indicated the email is encrypted.

For more information about the ``partition_msg`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/msg.py>`__.


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
      documents = partition_multiple_via_api(files=files, metadata_filenames=filenames)

For more information about the ``partition_multiple_via_api`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/api.py>`__.


``partition_odt``
------------------

The ``partition_odt`` partitioning function pre-processes Open Office documents
saved in the ``.odt`` format. The function first converts the document
to ``.docx`` using ``pandoc`` and then processes it using ``partition_docx``.

Examples:

.. code:: python

  from unstructured.partition.odt import partition_odt

  elements = partition_odt(filename="example-docs/fake.odt")

For more information about the ``partition_odt`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/odt.py>`__.


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

For more information about the ``partition_org`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/org.py>`__.


``partition_pdf``
-----------------

The ``partition_pdf`` function segments a PDF document by using a document image analysis model.
If you set ``url=None``, the document image analysis model will execute locally. You need to install ``unstructured[local-inference]``
if you'd like to run inference locally.
If you set the URL, ``partition_pdf`` will make a call to a remote inference server.
``partition_pdf`` also includes a ``token`` function that allows you to pass in an authentication
token for a remote API call.

You can also specify what languages to use for OCR with the ``languages`` kwarg. For example,
use ``languages=["eng", "deu"]`` to use the English and German language packs. See the
`Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and
install instructions. OCR is only applied if the text is not already available in the PDF document.

Examples:

.. code:: python

  from unstructured.partition.pdf import partition_pdf

  # Returns a List[Element] present in the pages of the parsed pdf document
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf")

  # Applies the English and Swedish language pack for ocr. OCR is only applied
  # if the text is not available in the PDF.
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf", languages=["eng", "swe"])


The ``strategy`` kwarg controls the method that will be used to process the PDF.
The available strategies for PDFs are ``"auto"``, ``"hi_res"``, ``"ocr_only"``, and ``"fast"``.

* The ``"auto"`` strategy will choose the partitioning strategy based on document characteristics and the function kwargs. If ``infer_table_structure`` is passed, the strategy will be ``"hi_res"`` because that is the only strategy that currently extracts tables for PDFs. Otherwise, ``"auto"`` will choose ``"fast"`` if the PDF text is extractable and ``"ocr_only"`` otherwise. ``"auto"`` is the default strategy.

* The ``"hi_res"`` strategy will identify the layout of the document using ``detectron2``. The advantage of `"hi_res"` is that it uses the document layout to gain additional information about document elements. We recommend using this strategy if your use case is highly sensitive to correct classifications for document elements. If ``detectron2`` is not available, the ``"hi_res"`` strategy will fall back to the ``"ocr_only"`` strategy.

* The ``"ocr_only"`` strategy runs the document through Tesseract for OCR and then runs the raw text through ``partition_text``. Currently, ``"hi_res"`` has difficulty ordering elements for documents with multiple columns. If you have a document with multiple columns that does not have extractable text, we recommend using the ``"ocr_only"`` strategy. ``"ocr_only"`` falls back to ``"fast"`` if Tesseract is not available and the document has extractable text.

* The ``"fast"`` strategy will extract the text using ``pdfminer`` and process the raw text with ``partition_text``. If the PDF text is not extractable, ``partition_pdf`` will fall back to ``"ocr_only"``. We recommend using the ``"fast"`` strategy in most cases where the PDF has extractable text.

To extract images and elements as image blocks from a PDF, it is mandatory to set ``strategy="hi_res"`` when setting ``extract_images_in_pdf=True``. With this configuration, detected images are saved in a specified directory or encoded within the file. However, keep in mind that ``extract_images_in_pdf`` is being phased out in favor of ``extract_image_block_types``. This option allows you to specify types of images or elements, like "Image" or "Table". If some extracted images have content clipped, you can adjust the padding by specifying two environment variables "EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD" and "EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD" (for example, EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD = 20, EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD = 10). For integrating these images directly into web applications or APIs, ``extract_image_block_to_payload`` can be used to convert them into ``base64`` format, including details about the image type. Lastly, the ``extract_image_block_output_dir`` can be used to specify the filesystem path for saving the extracted images when not embedding them in payloads.

Examples:

.. code:: python

  from unstructured.partition.pdf import partition_pdf

  partition_pdf(
      filename="path/to/your/pdf_file.pdf",                  # mandatory
      strategy="hi_res",                                     # mandatory to use ``hi_res`` strategy
      extract_images_in_pdf=True,                            # mandatory to set as ``True``
      extract_image_block_types=["Image", "Table"],          # optional
      extract_image_block_to_payload=False,                  # optional
      extract_image_block_output_dir="path/to/save/images",  # optional - only works when ``extract_image_block_to_payload=False``
      )


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

For more information about the ``partition_pdf`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/pdf.py>`__.


``partition_ppt``
---------------------

The ``partition_ppt`` partitioning function pre-processes Microsoft PowerPoint documents
saved in the ``.ppt`` format. This partition function uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_ppt`` can take a filename or file-like object.
``partition_ppt`` uses ``libreoffice`` to convert the file to ``.pptx`` and then
calls ``partition_pptx``. Ensure you have ``libreoffice`` installed
before using ``partition_ppt``.

Examples:

.. code:: python

  from unstructured.partition.ppt import partition_ppt

  elements = partition_ppt(filename="example-docs/fake-power-point.ppt")

For more information about the ``partition_ppt`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/ppt.py>`__.


``partition_pptx``
---------------------

The ``partition_pptx`` partitioning function pre-processes Microsoft PowerPoint documents
saved in the ``.pptx`` format. This partition function uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_pptx`` can take a filename or file-like object
as input, as shown in the two examples below.

Examples:

.. code:: python

  from unstructured.partition.pptx import partition_pptx

  elements = partition_pptx(filename="example-docs/fake-power-point.pptx")

  with open("example-docs/fake-power-point.pptx", "rb") as f:
      elements = partition_pptx(file=f)

For more information about the ``partition_pptx`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/pptx.py>`__.


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

For more information about the ``partition_rst`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/rst.py>`__.


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

For more information about the ``partition_rtf`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/rtf.py>`__.


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

For more information about the ``partition_text`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/text.py>`__.


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

For more information about the ``partition_tsv`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/tsv.py>`__.


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
    elements = partition_via_api(file=f, metadata_filename=filename, api_key="MY_API_KEY")


You can pass additional settings such as ``strategy``, ``languages`` and ``encoding`` to the
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

For more information about the ``partition_via_api`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/api.py>`__.


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

For more information about the ``partition_xlsx`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/xlsx.py>`__.


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

For more information about the ``partition_xml`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/partition/xml.py>`__.
