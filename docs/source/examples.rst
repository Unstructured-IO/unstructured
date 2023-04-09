Examples
========

The following are some examples of how to use the library to parse documents. You can find
example documents in the
`example-docs <https://github.com/Unstructured-IO/unstructured/tree/main/example-docs>`_, along
with instructions on how to download additional documents that are too large to store in the
repo.


##########################################
Sentiment Analysis Labeling in LabelStudio
##########################################

The following workflow will show how to format and upload the risk section from an SEC filing
to LabelStudio for a sentiment analysis labeling task. In addition to the ``unstructured``
library, this example assumes you have `LabelStudio <https://labelstud.io/guide/#Quick-start>`_ 
installed and running locally.


In addition to the ``unstructured`` library, this examples assumes you have the
`SEC pipeline <https://github.com/Unstructured-IO/pipeline-sec-filings>`_ repo installed and
on your Python path, as well `LabelStudio <https://labelstud.io/guide/#Quick-start>`_ installed
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

    # The resulting JSON file is ready to be uploaded to LabelStudio
    with open("label-studio.json", "w") as f:
        json.dump(label_studio_data, f, indent=4)


At this point, you can go into the LabelStudio UI and select ``Create`` to create a new project.
Upload your sample ``label-studio.json`` file and select ``Text Classification`` for your
labeling setup, and you're good to go.


You can also create a new project in LabelStudio through
the API by running the following command. Hit ``Account & Settings`` under your user name to find your
API token. First, use the `create project <https://labelstud.io/api#operation/api_projects_create>`_ call to
create a new project.
After creating a project, upload data using the following command. The project ID will come from the
response of the create project call. For existing projects, you can find the project ID in the URL for
the project.

.. code:: bash

    curl -H 'Authorization: Token ${LABELSTUDIO_TOKEN}' \
    -X POST 'http://localhost:8080/api/projects/{project_id}/import' \
    -F 'file=@label-studio.json'

At this point, you're good to go to start labeling in the LabelStudio UI.


##################################
Extracting Metadata from Documents
##################################

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


###########################
Exploring Source Documents
###########################

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

