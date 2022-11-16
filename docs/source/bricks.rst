Bricks
======

The ``unstructured`` library provides bricks to make it quick and
easy to parse documents and create new pre-processing pipelines. The following documents
bricks currently available in the library.


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
Partitioning
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

The partitioning bricks in ``unstructured`` differentiate between different sections
of text in a document. For example, the partitioning bricks can help distinguish between
titles, narrative text, and tables.

``is_bulleted_text``
----------------------

Uses regular expression patterns to check if a snippet of text is a bullet point. Only
triggers if the bullet point appears at the start of the snippet.

Examples:

.. code:: python

  from unstructured.nlp.partition import is_bulleted_text

  ***REMOVED*** Returns True
  is_bulleted_text("● An excellent point!")

  ***REMOVED*** Returns False
  is_bulleted_text("I love Morse Code! ●●●")


``is_possible_narrative_text``
------------------------------

The ``is_possible_narrative_text`` function determines if a section of text is a candidate
for consideration as narrative text. The function performs the following checks on input text:

* Empty text cannot be narrative text
* Text that is all numeric cannot be narrative text
* Text that does not contain a verb cannot be narrative text
* Text that exceeds the specified caps ratio cannot be narrative text. The threshold
  is configurable with the ``cap_threshold`` kwarg. To ignore this check, you can set
  ``cap_threshold=1.0``. You may want to ignore this check when dealing with text
  that is all caps.


Examples:

.. code:: python

  from unstructured.nlp.partition import is_possible_narrative_text

  ***REMOVED*** Returns True because the example passes all the checks
  example_1 = "Make sure you brush your teeth before you go to bed."
  is_possible_narrative_text(example_1)

  ***REMOVED*** Returns False because the text exceeds the caps ratio and does not contain a verb
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_narrative_text(example_2)

  ***REMOVED*** Returns True because the text has a verb and does not exceed the cap_threshold
  example_3 = "OLD MCDONALD HAD A FARM"
  is_possible_narrative_text(example_3, cap_threshold=1.0)


``is_possible_title``
---------------------

The ``is_possible_title`` function determines if a section of text is a candidate
for consideration as a title. The function performs the following checks:

* Empty text cannot be a title
* Text that is all numeric cannot be a title
* If a title contains more than one sentence that exceeds a certain length, it cannot be a title.
  Sentence length threshold is controlled by the ``sentence_min_length`` kwarg and defaults to 5.


Examples:

.. code:: python

  from unstructured.nlp.partition import is_possible_title

  ***REMOVED*** Returns True because the text passes all the tests
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_title(example_2)

  ***REMOVED*** Returns True because there is only one sentence
  example_2 = "Make sure you brush your teeth before you go to bed."
  is_possible_title(example_2, sentence_min_length=5)

  ***REMOVED*** Returns False because there are two sentences
  example_3 = "Make sure you brush your teeth. Do it before you go to bed."
  is_possible_title(example_3, sentence_min_length=5)


``contains_verb``
-----------------

Checks if the text contains a verb. This is used in ``is_possible_narrative_text``, but can
be used independently as well. The function identifies verbs using the NLTK part of speech
tagger. The following part of speech tags are identified as verbs:

* ``VB``
* ``VBG``
* ``VBD``
* ``VBN``
* ``VBP``
* ``VBZ``

Examples:

.. code:: python

  from unstructured.nlp.partition import contains_verb

  ***REMOVED*** Returns True because the text contains a verb
  example_1 = "I am going to run to the store to pick up some milk."
  contains_verb(example_1)

  ***REMOVED*** Returns False because the text does not contain a verb
  example_2 = "A friendly dog"
  contains_verb(example_2)


``sentence_count``
------------------

Counts the number of sentences in a section of text. Optionally, you can only include
sentences that exceed a specified word count. Punctuation counts as a word token
in the sentence. The function uses the NLTK sentence and word tokeniers to identify
distinct sentences and words.

Examples:

.. code:: python

  from unstructured.nlp.partition import sentence_count

  example = "Look at me! I am a document with two sentences."

  ***REMOVED*** Returns 2 because the example contains two sentences
  sentence_count(example)

  ***REMOVED*** Returns 1 because the first sentence in the example does not contain five word tokens.
  sentence_count(example, min_length=5)


``exceeds_cap_ratio``
---------------------

Determines if the section of text exceeds the specified caps ratio. Used in
``is_possible_narrative_text`` and ``is_possible_title``, but can be used independently
as well. You can set the caps threshold using the ``threshold`` kwarg. The threshold
defaults to ``0.3``. Only runs on sections of text that are a single sentence.

Examples:

.. code:: python

  from unstructured.nlp.partition import exceeds_cap_ratio

  ***REMOVED*** Returns True because the text is more than 30% caps
  example_1 = "LOOK AT ME I AM YELLING"
  exceeds_cap_ratio(example_1)

  ***REMOVED*** Returns False because the text is less than 30% caps
  example_2 = "Look at me, I am no longer yelling"
  exceeds_cap_ratio(example_2)

  ***REMOVED*** Returns False because the text is more than 1% caps
  exceeds_cap_ratio(example_2, threshold=0.01)
  
  
``partition_pdf``
---------------------

The ``partition_pdf`` function segments a PDF document by calling the document image analysis API. 
The intent of the parameters ``url`` and ``token`` is to allow users to self host an inference API,
if desired.

Examples:

.. code:: python

  from unstructured.nlp.partition import partition_pdf

  ***REMOVED*** Returns a List[Element] present in the pages of the parsed pdf document
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf")


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
Cleaning
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

The cleaning bricks in ``unstructured`` remove unwanted text from source documents.
Examples include removing extra whitespace, boilerplate, or sentence fragments.


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

  ***REMOVED*** Returns "an excellent point!"
  clean("● An excellent point!", bullets=True, lowercase=True)

  ***REMOVED*** Returns "ITEM 1A: RISK FACTORS"
  clean("ITEM 1A:     RISK-FACTORS", whitespace=True, dashes=True)


``clean_bullets``
-----------------

Removes bullets from the beginning of text. Bullets that do not appear at the beginning of the
text are not removed.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_bullets

  ***REMOVED*** Returns "An excellent point!"
  clean_bullets("● An excellent point!")

  ***REMOVED*** Returns "I love Morse Code! ●●●"
  clean_bullets("I love Morse Code! ●●●")


``clean_extra_whitespace``
--------------------------

Removes extra whitespace from a section of text. Also handles special characters
such as ``\xa0`` and newlines.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_extra_whitespace

  ***REMOVED*** Returns "ITEM 1A: RISK FACTORS"
  clean_extra_whitespace("ITEM 1A:     RISK FACTORS\n")


``clean_dashes``
----------------

Removes dashes from a section of text. Also handles special characters
such as ``\u2013``.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_dashes

  ***REMOVED*** Returns "ITEM 1A: RISK FACTORS"
  clean_dashes("ITEM 1A: RISK-FACTORS\u2013")


``clean_trailing_punctuation``
-------------------------------

Removes trailing punctuation from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_trailing_punctuation

  ***REMOVED*** Returns "ITEM 1A: RISK FACTORS"
  clean_trailing_punctuation("ITEM 1A: RISK FACTORS.")


``replace_unicode_quotes``
--------------------------

Replaces unicode quote characters such as ``\x91`` in strings.

Examples:

.. code:: python

  from unstructured.cleaners.core import replace_unicode_quotes

  ***REMOVED*** Returns "“A lovely quote!”"
  replace_unicode_characters("\x93A lovely quote!\x94")

  ***REMOVED*** Returns ""‘A lovely quote!’"
  replace_unicode_characters("\x91A lovely quote!\x92")


``remove_punctuation``
--------------------------

Removes ASCII and unicode punctuation from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import remove_punctuation

  ***REMOVED*** Returns "A lovely quote"
  replace_unicode_characters("“A lovely quote!”")

  ***REMOVED*** Returns ""
  replace_unicode_characters("'()[]{};:'\",.?/\\-_")


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

  ***REMOVED*** Returns "This is the best summary of all time!"
  clean_prefix(text, r"(SUMMARY|DESCRIPTION):", ignore_case=True)


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

  ***REMOVED*** Returns "The end!"
  clean_postfix(text, r"(END|STOP)", ignore_case=True)


``extract_text_before``
-----------------------

Extracts text that occurs before the specified pattern.

Options:

* If ``index`` is set, extract before the ``(index + 1)``th occurence of the pattern. The default is ``0``.
* Strips leading whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_before

  text = "Here I am! STOP Look at me! STOP I'm flying! STOP"

  ***REMOVED*** Returns "Here I am!"
  extract_text_before(text, r"STOP")


``extract_text_after``
----------------------

Extracts text that occurs after the specified pattern.

Options:

* If ``index`` is set, extract after the ``(index + 1)``th occurence of the pattern. The default is ``0``.
* Strips trailing whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_after

  text = "SPEAKER 1: Look at me, I'm flying!"

  ***REMOVED*** Returns "Look at me, I'm flying!"
  extract_text_after(text, r"SPEAKER \d{1}:")


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
Staging
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

Staging bricks in ``unstructured`` prepare extracted text for downstream tasks such
as machine learning inference and data labeling.

``convert_to_isd``
------------------

Converts outputs to the initial structured data (ISD) format. This is the default format
for returning data in Unstructured pipeline APIs.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.base import convert_to_isd

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  isd = convert_to_isd(elements)


``isd_to_elements``
-------------------

Converts outputs from initial structured data (ISD) format back to a list of ``Text`` elements.

Examples:

.. code:: python

  from unstructured.staging.base import isd_to_elements

  isd = [
    {"text": "My Title", "type": "Title"},
    {"text": "My Narrative", "type": "NarrativeText"}
  ]

  ***REMOVED*** elements will look like:
  ***REMOVED*** [ Title(text="My Title"), NarrativeText(text="My Narrative")]
  elements = isd_to_elements(isd)


``convert_to_isd_csv``
----------------------

Converts outputs to the initial structured data (ISD) format as a CSV string.

Examples:

.. code:: python

  from unstructured.documents.elements import Title, NarrativeText
  from unstructured.staging.base import convert_to_isd_csv

  elements = [Title(text="Title"), NarrativeText(text="Narrative")]
  isd_csv = convert_to_isd_csv(elements)


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

    chunks = stage_for_transformers([NarrativeText(text=text)], tokenizer)

    results = [nlp(chunk) for chunk in chunks]


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

  ***REMOVED*** The resulting JSON file is ready to be uploaded to LabelStudio
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

  ***REMOVED*** The resulting JSON file is ready to be uploaded to LabelStudio
  ***REMOVED*** with annotations included
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

  ***REMOVED*** The resulting JSON file is ready to be uploaded to LabelStudio
  ***REMOVED*** with annotations included
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

  ***REMOVED*** The resulting JSON file is ready to be uploaded to LabelStudio
  ***REMOVED*** with annotations included
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)


See the `LabelStudio docs <https://labelstud.io/tags/labels.html>`_ for a full list of options
for labels and annotations.


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

  ***REMOVED*** The resulting JSON file is ready to be used with Prodigy
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

  ***REMOVED*** The resulting jsonl file is ready to be used with Prodigy.
  save_as_jsonl(prodigy_data, "prodigy.jsonl")



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

  ***REMOVED*** The resulting CSV file is ready to be used with Prodigy
  with open("prodigy.csv", "w") as csv_file:
      csv_file.write(prodigy_csv_data)



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

  ***REMOVED*** The S3 Bucket name where data files should be uploaded.
  S3_BUCKET_NAME = "labelbox-staging-bucket"

  ***REMOVED*** The S3 key prefix (I.e. directory) where data files should be stored.
  S3_BUCKET_KEY_PREFIX = "data/"

  ***REMOVED*** The URL prefix where the data files will be accessed.
  S3_URL_PREFIX = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{S3_BUCKET_KEY_PREFIX}"
  
  ***REMOVED*** The local output directory where the data files will be staged for uploading to a Cloud Storage service.
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

  ***REMOVED*** The resulting JSON config file is ready to be used with LabelBox.
  with open("config.json", "w+") as labelbox_config_file:
      json.dump(labelbox_config, labelbox_config_file, indent=4)


  ***REMOVED*** Upload staged data files to S3 from local output directory.
  def upload_staged_files():
      import boto3
      s3 = boto3.client("s3")
      for filename in os.listdir(LOCAL_OUTPUT_DIRECTORY):
          filepath = os.path.join(LOCAL_OUTPUT_DIRECTORY, filename)
          upload_key = os.path.join(S3_BUCKET_KEY_PREFIX, filename)
          s3.upload_file(filepath, Bucket=S3_BUCKET_NAME, Key=upload_key)

  upload_staged_files()

``stage_for_datasaur``
--------------------------
Formats a list of ``Text`` elements as input to token based tasks in Datasaur.

Example: 

.. code:: python

  from unstructured.staging.datasaur import stage_for_datasaur
  elements  = [Text("Text1"),Text("Text2")]
  datasaur_data = stage_for_datasaur(elements)

The output is a list of dictionaries, each one with two keys:
"text" with the content of the element and 
"entities" with an empty list.
