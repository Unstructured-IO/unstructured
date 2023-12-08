.. role:: raw-html(raw)
    :format: html

.. _metadata-label:

Metadata
========

The ``unstructured`` package tracks a variety of metadata about Elements extracted from documents.
Tracking metadata enables users to filter document elements downstream based on element metadata of interest.
For example, a user may be interested in selected document elements from a given page number
or an e-mail with a given subject line.

Metadata is tracked at the element level. You can extract the metadata for a given document element
with ``element.metadata``. For a dictionary representation, use ``element.metadata.to_dict()``.


######################
Common Metadata Fields
######################

All document types return the following metadata fields when the information is available from
the source file:

+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Metadata Field Name         | Short Description                                        | Details                                                                                                                                                                                                                                                                                     |
+=============================+==========================================================+=============================================================================================================================================================================================================================================================================================+
| filename                    | Filename                                                 |                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| file_directory              | File Directory                                           |                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| last_modified               | Last Modified Date                                       |                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| filetype                    | File Type                                                |                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| coordinates                 | XY Bounding Box Coordinates                              | See notes below for further details about the bounding box.                                                                                                                                                                                                                                 |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| parent_id                   | Element Hierarchy (Parent ID)                            | `parent_id` may be used to infer where an element resides within the overall hierarchy of a document. For instance, a `NarrativeText` element may have a `Title` element as a parent (a "sub-title"), which in turn may have another `Title` element as its parent (a "title).              |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| category_depth              | Element Depth relative to                                | Category depth is the depth of an element relative to other elements of the same category. It's set by a document partitioner and enables the hierarchy post-processor to compute more accurate hierarchies.                                                                                |
|                             | other elements of the same category                      | Category depth may be set using native document hierarchies, e.g.  reflecting \<H1>, \<H2>, or `\<H3>` tags within an HTML document or the indentation level of a bulleted list item in a Word document.                                                                                    |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| text_as_html                | HTML representation of extracted tables                  |  Only applicable to table elements.                                                                                                                                                                                                                                                         |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| languages                   | Document Languages                                       | At document level or element level. List is ordered by probability of being the primary language of the text.                                                                                                                                                                               |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| emphasized_text_contents    | Emphasized text (bold or italic) in the original document|                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| emphasized_text_tags        | Tags on text that is emphasized in the original document |                                                                                                                                                                                                                                                                                             |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| is_continuation             | True if element is a continuation of a previous element  | Only relevant for chunking, if an element was divided into two due to ``max_characters``.                                                                                                                                                                                                   |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| detection_class_prob        | Detection model class probabilities                      | From unstructured-inference, hi-res strategy.                                                                                                                                                                                                                                               |
+-----------------------------+----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

:raw-html:`<br />`
Notes on common metadata fields:

Metadata for Document Hierarchy: ``parent_id`` and ``category_depth``
----------------------------------------------------------------------

*Parent ID* and *Category Depth* enhance hierarchy detection to identify the document structure in various file formats. It measures the relative depth of an element within its category. This is especially useful in documents with native hierarchies like HTML or Word files, where elements like headings or list items inherently define structure.

**Implementations:**

- **Parent ID:** Introduction of a ``parent_id`` metadata, identifying the parent element.
- **Category Depth:** Introduction of a ``category_depth`` metadata, identifying the element's depth level.
- **Rule set for hierarchy assignment:** Elements are sequentially processed against a ruleset, which set the Parent IDs and Category Depths, based on predetermined or custom rules.


Hierarchy in DOCX Files
***********************

The process of enhancing hierarchy detection by determining ``category_depth`` includes:

1. Evaluating the paragraph item for an indentation level (ilvl) xpath, commonly found in list bullet/number formats. If an indentation level is present, it is used as the category depth.
2. Inspecting the paragraph style name for any indications of category depth, such as differences between 'Heading 1' and 'Heading 2' or various list bullet styles. The detected category depth is used, or it defaults to 0 if none is found.
3. The paragraph's indentation level (ilvl) is assessed based on its style name. This involves a detailed lookup beyond the paragraph's metadata, as docx files have predefined ilvls for different style names. This aspect is in development, with the existing methods sufficiently addressing most scenarios.


Hierarchy in PPTX Files
***********************

The enhancement of hierarchy detection in determining category depth is achieved as follows:

1. Examining if the paragraph within the ``python-pptx`` document has a level parameter. When present, this level is adopted as the ``category_depth``.
2. In cases where the evaluated shape is a title and the content is neither a bullet nor an email, the element is designated as a ``Title``. The depth is assigned based on the paragraph's sequence (e.g., the first line in the title shape is depth 0, the second line is depth 1, and so on).
3. For situations where the shape is not a title but the paragraph is, the depth is set to the level plus one. This ensures that paragraph titles have a minimum depth of 1, positioning them appropriately under the main slide title element.


coordinates
-----------

Some document types support location data for the elements, usually in the form of bounding boxes.
If it exists, an element's location data is available with ``element.metadata.coordinates``.

The ``coordinates`` property of an ``ElementMetadata`` stores:

* ``points`` : These specify the corners of the bounding box starting from the top left corner and
  proceeding counter-clockwise. The points represent pixels, the origin is in the top left and
  the ``y`` coordinate increases in the downward direction.
* ``system``: The points have an associated coordinate system. A typical example of a coordinate system is
  ``PixelSpace``, which is used for representing the coordinates of images. The coordinate system has a
  name, orientation, layout width, and layout height.

Information about the element’s coordinates (including the coordinate system name, coordinate points,
the layout width, and the layout height) can be accessed with `element.to_dict()["metadata"]["coordinates"]`.

The coordinates of an element can be changed to a new coordinate system by using the
``Element.convert_coordinates_to_new_system`` method. If the ``in_place`` flag is ``True``, the
coordinate system and points of the element are updated in place and the new coordinates are
returned. If the ``in_place`` flag is ``False``, only the altered coordinates are returned.

.. code:: python

	from unstructured.documents.elements import Element
	from unstructured.documents.coordinates import PixelSpace, RelativeCoordinateSystem

	coordinates = ((10, 10), (10, 100), (200, 100), (200, 10))
	coordinate_system = PixelSpace(width=850, height=1100)

	element = Element(coordinates=coordinates, coordinate_system=coordinate_system)
	print(element.metadata.coordinates.to_dict())
	print(element.metadata.coordinates.system.orientation)
	print(element.metadata.coordinates.system.width)
	print(element.metadata.coordinates.system.height)

	element.convert_coordinates_to_new_system(RelativeCoordinateSystem(), in_place=True)
	# Should now be in terms of new coordinate system
	print(element.metadata.coordinates.to_dict())
	print(element.metadata.coordinates.system.orientation)
	print(element.metadata.coordinates.system.width)
	print(element.metadata.coordinates.system.height)

###########################################
Additional Metadata Fields by Document Type
###########################################

+-------------------------+---------------------+--------------------------------------------------------+
| Field Name              | Applicable Doc Types| Short Description                                      |
+=========================+=====================+========================================================+
| page_number             | DOCX,PDF, PPT,XLSX  | Page Number                                            |
+-------------------------+---------------------+--------------------------------------------------------+
| page_name               | XLSX                | Sheet Name in Excel document                           |
+-------------------------+---------------------+--------------------------------------------------------+
| sent_from               | EML                 | Email Sender                                           |
+-------------------------+---------------------+--------------------------------------------------------+
| sent_to                 | EML                 | Email Recipient                                        |
+-------------------------+---------------------+--------------------------------------------------------+
| subject                 | EML                 | Email Subject                                          |
+-------------------------+---------------------+--------------------------------------------------------+
| attached_to_filename    | MSG                 | filename that attachment file is attached to           |
+-------------------------+---------------------+--------------------------------------------------------+
| header_footer_type      | Word Doc            | Pages a header or footer applies to: "primary",        |
|                         |                     | "even_only", and "first_page"                          |
+-------------------------+---------------------+--------------------------------------------------------+
| link_urls               | HTML                | The url associated with a link in a document.          |
+-------------------------+---------------------+--------------------------------------------------------+
| link_texts              | HTML                | The text associated with a link in a document.         |
+-------------------------+---------------------+--------------------------------------------------------+
| links                   | HTML                | List of {”text”: “<the text>, “url”: <the url>} items. |
|                         |                     | Note: this element will be removed in the near future  |
|                         |                     | in favor of the above link_urls and link_texts.        |
+-------------------------+---------------------+--------------------------------------------------------+
| section                 | EPUB                | Book section title corresponding to table of contents  |
+-------------------------+---------------------+--------------------------------------------------------+

:raw-html:`<br />`
Notes on additional metadata by document type:

Email
-----

Emails will include ``sent_from``, ``sent_to``, and ``subject`` metadata.
``sent_from`` is a list of strings because the `RFC 822 <https://www.rfc-editor.org/rfc/rfc822>`_
spec for emails allows for multiple sent from email addresses.


Microsoft Excel Documents
--------------------------

For Excel documents, ``ElementMetadata`` will contain a ``page_name`` element, which corresponds
to the sheet name in the Excel document.


Microsoft Word Documents
-------------------------

Headers and footers in Word documents include a ``header_footer_type`` indicating which page
a header or footer applies to. Valid values are ``"primary"``, ``"even_only"``, and ``"first_page"``.


##############################
Data Connector Metadata Fields
##############################

Documents processed through unstructured-ingest connectors include additional document metadata. These additional fields only ever appear if the source document was processed by a connector.

Common Data Connector Metadata Fields
-------------------------------------

- Data Source metadata (on json output):
    - url
    - version
    - date created
    - date modified
    - date processed
    - record locator
- Record locator is specific to each connector

Additional Metadata Fields by Connector Type (via record locator)
-----------------------------------------------------------------

- airtable
    - base id
    - table id
    - view id
- azure (from fsspec)
    - protocol
    - remote file path
- box (from fsspec)
    - protocol
    - remote file path
- confluence
    - url
    - page id
- discord
    - channel
- dropbox (from fsspec)
    - protocol
    - remote file path
- elasticsearch
    - url
    - index name
    - document id
- fsspec
    - protocol
    - remote file path
- google drive
    - drive id
    - file id
- gcs (from fsspec)
    - protocol
    - remote file path
- jira
    - base url
    - issue key
- onedrive
    - user pname
    - server relative path
- outlook
    - message id
    - user email
- s3 (from fsspec)
    - protocol
    - remote file path
- sharepoint
    - server path
    - site url
- wikipedia
    - page title
    - page url


##########################
Advanced Metadata Options
##########################

Extract Metadata with Regexes
------------------------------

``unstructured`` allows users to extract additional metadata with regexes using the ``regex_metadata`` kwarg.
Here is an example of how to extract regex metadata:


.. code:: python

  from unstructured.partition.text import partition_text

  text = "SPEAKER 1: It is my turn to speak now!"
  elements = partition_text(text=text, regex_metadata={"speaker": r"SPEAKER \d{1,3}:"})
  elements[0].metadata.regex_metadata

The result will look like:


.. code:: python

  {'speaker':
    [
      {
        'text': 'SPEAKER 1:',
        'start': 0,
        'end': 10,
     }
    ]
  }
