Metadata
========

The ``unstructured`` package tracks a variety of metadata about Elements extracted from documents.
Tracking metadata enables users to filter document elements downstream based on element metadata of interest.
For example, a user may be interested in selected document elements from a given page number
or an e-mail with a given subject line.

Metadata is tracked at the element level. You can extract the metadata for a given document element
with ``element.metadata``. For a dictionary representation, use ``element.metadata.to_dict()``.
All document types return the following metadata fields when the information is available from
the source file:

* ``filename``
* ``file_directory``
* ``date``
* ``filetype``
* ``page_number``


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


Webpages
---------

Elements from webpages will include a ``url`` metadata field, corresponding to the URL for the webpage.



##########################
Advanced Metadata Options
###########################



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
