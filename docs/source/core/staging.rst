#######
Staging
#######

.. warning::
    The ``Staging`` brick is being deprecated in favor of the new and more comprehensive ``Destination Connectors``. To explore the complete list and usage, please refer to `Destination Connectors documentation <https://unstructured-io.github.io/unstructured/ingest/destination_connectors.html>`__.

    Note: We are constantly expanding our collection of destination connectors. If you wish to request a specific Destination Connector, you're encouraged to submit a Feature Request on the `Unstructured GitHub repository <https://github.com/Unstructured-IO/unstructured/issues/new/choose>`__.


Staging functions in the ``unstructured`` package help prepare your data for ingestion into downstream systems.
A staging function accepts a list of document elements as input and return an appropriately formatted dictionary as output.
In the example below, we get our narrative text samples prepared for ingestion into LabelStudio using
``the stage_for_label_studio`` function.
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

For more information about the ``convert_to_csv`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`__.


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

For more information about the ``convert_to_dataframe`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`__.


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

For more information about the ``convert_to_dict`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`__.


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

For more information about the ``dict_to_elements`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/base.py>`__.


``stage_csv_for_prodigy``
--------------------------

Formats outputs in CSV format for use with `Prodigy <https://prodi.gy/docs/api-loaders>`__. After running ``stage_csv_for_prodigy``, you can
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

For more information about the ``stage_csv_for_prodigy`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/prodigy.py>`__.


``stage_for_argilla``
--------------------------

Convert a list of ``Text`` elements to an `Argilla Dataset <https://docs.argilla.io/en/latest/reference/python/python_client.html#python-ref-datasets>`__.
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

For more information about the ``stage_for_argilla`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/argilla.py>`__.


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

For more information about the ``stage_for_baseplate`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/baseplate.py>`__.


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

You can also specify entities in the ``stage_for_datasaur`` function. Entities
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

For more information about the ``stage_for_datasaur`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/datasaur.py>`__.


``stage_for_label_box``
--------------------------

Formats outputs for use with `LabelBox <https://docs.labelbox.com/docs/overview>`__. LabelBox accepts cloud-hosted data
and does not support importing text directly. The ``stage_for_label_box`` does the following:

* Stages the data files in the ``output_directory`` specified in function arguments to be uploaded to a cloud storage service.
* Returns a config of type ``List[Dict[str, Any]]`` that can be written to a ``json`` file and imported into LabelBox.

**Note:** ``stage_for_label_box`` does not upload the data to remote storage such as S3. Users can upload the data to S3
using ``aws s3 sync ${output_directory} ${url_prefix}`` after running the ``stage_for_label_box`` staging function.

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

For more information about the ``stage_for_label_box`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/label_box.py>`__.


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

For more information about the ``stage_for_label_studio`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/label_studio.py>`__.


``stage_for_prodigy``
--------------------------

Formats outputs in JSON format for use with `Prodigy <https://prodi.gy/docs/api-loaders>`__. After running ``stage_for_prodigy``, you can
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

For more information about the ``stage_for_prodigy`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/prodigy.py>`__.


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

For more information about the ``stage_for_transformers`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/huggingface.py>`__.


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

For more information about the ``stage_for_weaviate`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/staging/weaviate.py>`__.

