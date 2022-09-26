Bricks
======

The ``unstructured`` library provides bricks to make it quick and
easy to parse documents and create new pre-processing pipelines. The following documents
bricks currently available in the library.


############
Partitioning
############

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

  # Returns True
  is_bulleted_text("● An excellent point!")

  # Returns False
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

  # Returns True because the example passes all the checks
  example_1 = "Make sure you brush your teeth before you go to bed."
  is_possible_narrative_text(example_1)

  # Returns False because the text exceeds the caps ratio and does not contain a verb
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_narrative_text(example_2)

  # Returns True because the text has a verb and does not exceed the cap_threshold
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

  # Returns True because the text passes all the tests
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_title(example_2)

  # Returns True because there is only one sentence
  example_2 = "Make sure you brush your teeth before you go to bed."
  is_possible_title(example_2, sentence_min_length=5)

  # Returns False because there are two sentences
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

  # Returns True because the text contains a verb
  example_1 = "I am going to run to the store to pick up some milk."
  contains_verb(example_1)

  # Returns False because the text does not contain a verb
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

  # Returns 2 because the example contains two sentences
  sentence_count(example)

  # Returns 1 because the first sentence in the example does not contain five word tokens.
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

  # Returns True because the text is more than 30% caps
  example_1 = "LOOK AT ME I AM YELLING"
  exceeds_cap_ratio(example_1)

  # Returns False because the text is less than 30% caps
  example_2 = "Look at me, I am no longer yelling"
  exceeds_cap_ratio(example_2)

  # Returns False because the text is more than 1% caps
  exceeds_cap_ratio(example_2, threshold=0.01)


########
Cleaning
########

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

  # Returns "an excellent point!"
  clean("● An excellent point!", bullets=True, lowercase=True)

  # Returns "ITEM 1A: RISK FACTORS"
  clean("ITEM 1A:     RISK-FACTORS", whitespace=True, dashes=True)


``clean_bullets``
-----------------

Removes bullets from the beginning of text. Bullets that do not appear at the beginning of the
text are not removed.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_bullets

  # Returns "An excellent point!"
  clean_bullets("● An excellent point!")

  # Returns "I love Morse Code! ●●●"
  clean_bullets("I love Morse Code! ●●●")


``clean_extra_whitespace``
--------------------------

Removes extra whitespace from a section of text. Also handles special characters
such as ``\xa0`` and newlines.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_extra_whitespace

  # Returns "ITEM 1A: RISK FACTORS"
  clean_extra_whitespace("ITEM 1A:     RISK FACTORS\n")


``clean_dashes``
----------------

Removes dashes from a section of text. Also handles special characters
such as ``\u2013``.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_dashes

  # Returns "ITEM 1A: RISK FACTORS"
  clean_dashes("ITEM 1A: RISK-FACTORS\u2013")


``clean_trailing_punctuation``
-------------------------------

Removes trailing punctuation from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_trailing_punctuation

  # Returns "ITEM 1A: RISK FACTORS"
  clean_trailing_punctuation("ITEM 1A: RISK FACTORS.")


``replace_unicode_quotes``
--------------------------

Replaces unicode quote characters such as ``\x91`` in strings.

Examples:

.. code:: python

  from unstructured.cleaners.core import replace_unicode_quotes

  # Returns "“A lovely quote!”"
  replace_unicode_characters("\x93A lovely quote!\x94")

  # Returns ""‘A lovely quote!’"
  replace_unicode_characters("\x91A lovely quote!\x92")


``remove_punctuation``
--------------------------

Removes ASCII and unicode punctuation from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import remove_punctuation

  # Returns "A lovely quote"
  replace_unicode_characters("“A lovely quote!”")

  # Returns ""
  replace_unicode_characters("'()[]{};:'\",.?/\\-_")


#######
Staging
#######

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
  label_studio_data = stage_for_label_studio(elements)

  # The resulting JSON file is ready to be uploaded to LabelStudio
  with open("label_studio.json", "w") as f:
      json.dump(label_studio_data, f, indent=4)
