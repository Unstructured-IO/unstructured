Exploring Source Documents
==========================

The ``unstructured`` library includes tools for helping you explore source documents.
To get a summary of the size (in bytes) and type of documents in a directory, you can
use the ``get_directory_file_info`` function, as show below. The function will
recursively explore files in subdirectories.

.. code:: python

    from unstructured.file_utils.exploration import get_directory_file_info

    file_info = get_directory_file_info("example-docs")
    file_info.filetype.value_counts()


The output (``file_info``) is a ``pandas`` ``DataFrame``.
The result should look similar to:

.. code:: python

    FileType.EML     4
    FileType.TXT     3
    FileType.HTML    2
    FileType.XML     2
    FileType.PDF     2
    FileType.DOCX    1
    FileType.PPTX    1
    FileType.XLSX    1
    FileType.JPG     1
    Name: filetype, dtype: int64


You can also find the average file size by file type by using the following command


.. code:: python

    from unstructured.file_utils.exploration import get_directory_file_info

    file_info = get_directory_file_info("example-docs")
    file_info.groupby("filetype").mean()


The output should look similar to the following:

.. code:: python


                       filesize
    filetype
    FileType.DOCX  3.660200e+04
    FileType.EML   1.490885e+05
    FileType.HTML  1.228404e+06
    FileType.JPG   3.276400e+04
    FileType.PDF   2.429245e+06
    FileType.PPTX  2.832900e+04
    FileType.TXT   6.113333e+02
    FileType.XLSX  4.765000e+03
    FileType.XML   7.135000e+02

