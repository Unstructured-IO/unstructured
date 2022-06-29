Examples
========

The following are some examples of how to use the library to parse documents. You can find
example documents in the
`example-docs <https://github.com/Unstructured-IO/unstructured/tree/main/example-docs>`_, along
with instructions on how to download additional documents that are too large to store in the
repo.

###########
PDF Parsing
###########

Once installed, you can try the following using the
`layoutparser <https://arxiv.org/pdf/2103.15348.pdf>`_ paper as an example. The PDF
of the paper is available in the
`example-docs <https://github.com/Unstructured-IO/unstructured/tree/main/example-docs>`_ directory.

.. code:: python

    from unstructured.documents.pdf import PDFDocument

    doc = PDFDocument.from_file("example-docs/layout-parser-paper.pdf")
    print(doc)

At this point, ``print(doc)`` will print out a string representation of the PDF file. The
first page of output looks like the following:

.. code:: python

    """
    LayoutParser : A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis

    Zejiang Shen 1 ( (cid:0) ), Ruochen Zhang 2 , Melissa Dell 3 , Benjamin Charles Germain Lee 4 , Jacob Carlson 3 , and
    Weining Li 5

    Abstract. Recent advances in document image analysis (DIA) have been primarily driven by the application of neural
    networks. Ideally, research outcomes could be easily deployed in production and extended for further investigation.
    However, various factors like loosely organized codebases and sophisticated model conﬁgurations complicate the easy
    reuse of im- portant innovations by a wide audience. Though there have been on-going eﬀorts to improve reusability and
    simplify deep learning (DL) model development in disciplines like natural language processing and computer vision, none
    of them are optimized for challenges in the domain of DIA. This represents a major gap in the existing toolkit, as DIA
    is central to academic research across a wide range of disciplines in the social sciences and humanities. This paper
    introduces LayoutParser , an open-source library for streamlining the usage of DL in DIA research and applica- tions.
    The core LayoutParser library comes with a set of simple and intuitive interfaces for applying and customizing DL models
    for layout de- tection, character recognition, and many other document processing tasks. To promote extensibility,
    LayoutParser also incorporates a community platform for sharing both pre-trained models and full document digiti- zation
    pipelines. We demonstrate that LayoutParser is helpful for both lightweight and large-scale digitization pipelines in
    real-word use cases. The library is publicly available at https://layout-parser.github.io

    Keywords: Document Image Analysis · Deep Learning · Layout Analysis · Character Recognition · Open Source library ·
    Toolkit.

    Introduction

    Deep Learning(DL)-based approaches are the state-of-the-art for a wide range of document image analysis (DIA) tasks
    including document image classiﬁcation [11,
    """

The ``Document`` has a ``pages`` attribute consisting of ``Page`` object and the ``Page`` object
has an ``elements`` attribute consisting of ``Element`` objects. Sub-types of the ``Element`` class
represent different components of a document, such as ``NarrativeText`` and ``Title``. You can use
these normalized elements to zero in on the components of a document you most care about.

############
HTML Parsing
############

You can parse an HTML document using the following command.

.. code:: python

    from unstructured.documents.html import HTMLDocument

    doc = HTMLDocument.from_file("example-docs/example-10k.html")
    print(doc.pages[2])


You can also instantiate a document directly from an HTML string using the ``from_string`` method.
The output of this will be the following:

.. code:: python

    """
    SPECIAL NOTE REGARDING FORWARD-LOOKING STATEMENTS
    This report contains statements that do not relate to historical or current facts but are “forward-looking” statements. These statements relate to analyses and other information based on forecasts of future results and estimates of amounts not yet determinable. These statements may also relate to future events or trends, our future prospects and proposed new products, services, developments or business strategies, among other things. These statements can generally (although not always) be identified by their use of terms and phrases such as anticipate, appear, believe, could, would, estimate, expect, indicate, intent, may, plan, predict, project, pursue, will continue and other similar terms and phrases, as well as the use of the future tense.

    Actual results could differ materially from those expressed or implied in our forward-looking statements. Our future financial condition and results of operations, as well as any forward-looking statements, are subject to change and to inherent known and unknown risks and uncertainties. You should not assume at any point in the future that the forward-looking statements in this report are still valid. We do not intend, and undertake no obligation, to update our forward-looking statements to reflect future events or circumstances.
    """

If you then run:

.. code:: python

    doc.pages[2].elements

You'll get the following output, showing that the parser successfully differentiated between
titles and narrative text.

.. code:: python

    [<unstructured.documents.base.Title at 0x169cbe820>,
    <unstructured.documents.base.NarrativeText at 0x169cbe8e0>,
    <unstructured.documents.base.NarrativeText at 0x169cbe3a0>]


Creating HTML from XML with XSLT
--------------------------------

You can also convert XML files to HTML with the appropriate XSLT stylesheet. Note, XSLT
converts arbitrary XML to XML, so there's no guarantee the result will be HTML. Ensure
you're using a stylesheet designed to convert your specific XML to HTML. The workflow
for reading in a document with an XSLT stylesheet is as follows:

.. code:: python

  from unstructured.document.html import HTMLDocument

  doc = HTMLDocument.from_file(filename="example-docs/factbook.xml",
                               stylesheet="example-docs/factbook.xsl")

If you read from a stylesheet ``HTMLDocument`` will use the ``etree.XMLParser`` by default
instead of the ``etree.HTMLParser`` because ``HTMLDocument`` assumes you want to convert
your raw XML to HTML.
