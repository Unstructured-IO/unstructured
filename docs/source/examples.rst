Examples
========

The following are some examples of how to use the library to parse documents. You can find
example documents in the
`example-docs <https://github.com/Unstructured-IO/unstructured/tree/main/example-docs>`_, along
with instructions on how to download additional documents that are too large to store in the
repo.


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
Sentiment Analysis Labeling in LabelStudio
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

The following workflow will show how to format and upload the risk section from an SEC filing
to LabelStudio for a sentiment analysis labeling task. In addition to the ``unstructured``
library, this example assumes you have `LabelStudio <https://labelstud.io/guide/***REMOVED***Quick-start>`_ 
installed and running locally.


In addition to the ``unstructured`` library, this examples assumes you have the
`SEC pipeline <https://github.com/Unstructured-IO/pipeline-sec-filings>`_ repo installed and
on your Python path, as well `LabelStudio <https://labelstud.io/guide/***REMOVED***Quick-start>`_ installed
and running locally. First, we'll import dependencies create some dummy risk narrative sections.
For info on how to pull real SEC documents from EDGAR, see our
`SEC pipeline <https://github.com/Unstructured-IO/pipeline-sec-filings>`_ repo.

.. code:: python

    import json

    from unstructured.documents.elements import NarrativeText
    from unstructured.staging.label_studio import (
        stage_for_label_studio,
        LabelStudioAnnotation,
        LabelStudioPrediction,
        LabelStudioResult,
    )

    risk_section = [NarrativeText(text="Risk section 1"), NarrativeText(text="Risk section 2")]

Next, we'll prepopulate some annotations and predictions. Annotations and predictions are optional.
If you added annotations, the labeling examples will be pre-labeled in the LabelStudio UI. Predictions
are used for active learning in LabelStudio. If you include predictions, they will help determine
the order in which labeled examples are presented to annotators. Feel free to skip this step if you do
not need either of these features for your labeling task:


.. code:: python

    annotations = []
    for element in risk_section:
        annotations.append([LabelStudioAnnotation(
              result=[
                  LabelStudioResult(
                      type="choices",
                      value={"choices": ["Positive"]},
                      from_name="sentiment",
                      to_name="text",
                  )
              ]
          )]
        )


    predictions = []
    for element in risk_section:
        predictions.append([LabelStudioPrediction(
              result=[
                  LabelStudioResult(
                      type="choices",
                      value={"choices": ["Positive"]},
                      from_name="sentiment",
                      to_name="text",
                  )
              ],
              score=0.68
          )]
        )


Finally, we'll format the data for upload to LabelStudio. You can omit the ``annotations``
and ``predictions`` kwargs if you did't generated annotations or predictions.


.. code:: python

    label_studio_data = stage_for_label_studio(
        elements=risk_section,
        annotations=annotations,
        predictions=predictions,
        text_field="text",
        id_field="id"
    )

    ***REMOVED*** The resulting JSON file is ready to be uploaded to LabelStudio
    with open("label-studio.json", "w") as f:
        json.dump(label_studio_data, f, indent=4)


At this point, you can go into the LabelStudio UI and select ``Create`` to create a new project.
Upload your sample ``label-studio.json`` file and select ``Text Classification`` for your
labeling setup, and you're good to go.


You can also create a new project in LabelStudio through
the API by running the following command. Hit ``Account & Settings`` under your user name to find your
API token. First, use the `create project <https://labelstud.io/api***REMOVED***operation/api_projects_create>`_ call to
create a new project.
After creating a project, upload data using the following command. The project ID will come from the
response of the create project call. For existing projects, you can find the project ID in the URL for
the project.

.. code:: bash

    curl -H 'Authorization: Token ${LABELSTUDIO_TOKEN}' \
    -X POST 'http://localhost:8080/api/projects/{project_id}/import' \
    -F 'file=@label-studio.json'

At this point, you're good to go to start labeling in the LabelStudio UI.

***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
PDF Parsing
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

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

***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
HTML Parsing
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

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


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
Extracting Metadata from Documents
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

The ``unstructured`` library includes utilities for extracting metadata from
documents. Currently, there is support for extracting metadata from ``.docx``,
``.xlsx``, and ``.jpg`` documents. When you call these functions, the return type
is a ``Metadata`` data class that you can convert to a dictionary by calling the
``to_dict()`` method. If you extract metadata from a ``.jpg`` document, the output
will include EXIF metadata in the ``exif_data`` attribute, if it is available.
Here is an example of how to use the metadata extraction functionality:


.. code:: python

  from unstructured.file_utils.metadata import get_jpg_metadata

  filename = "example-docs/example.jpg"
  metadata = get_jpg_metadata(filename=filename)


You can also pass in a file-like object with:

.. code:: python

  from unstructured.file_utils.metadata import get_jpg_metadata

  filename = "example-docs/example.jpg"
  with open(filename, "rb") as f:
      metadata = get_jpg_metadata(file=f)


To extract metadata from ``.docx`` or ``.xlsx``, use ``get_docx_metadata`` and
``get_xlsx_metadata``. The interfaces are the same as ``get_jpg_metadata``.
