Extracting Metadata from Documents
==================================

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

