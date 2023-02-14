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

``partition``
--------------

The ``partition`` brick is the simplest way to partition a document in ``unstructured``.
If you call the ``partition`` function, ``unstructured`` will attempt to detect the
file type and route it to the appropriate partitioning brick. All partitioning bricks
called within ``partition`` are called using the defualt kwargs. Use the document-type
specific bricks if you need to apply non-default settings.
``partition`` currently supports ``.docx``, ``.pptx``, ``.eml``, ``.html``, ``.pdf``,
``.png``, ``.jpg``, and ``.txt`` files.
If you set the ``include_page_breaks`` kwarg to ``True``, the output will include page breaks. This is only supported for ``.pptx``, ``.html``, ``.pdf``,
``.png``, and ``.jpg``.


.. code:: python

  import docx

  from unstructured.partition.auto import partition

  document = docx.Document()
  document.add_paragraph("Important Analysis", style="Heading 1")
  document.add_paragraph("Here is my first thought.", style="Body Text")
  document.add_paragraph("Here is my second thought.", style="Normal")
  document.save("mydoc.docx")

  elements = partition(filename="mydoc.docx")

  with open("mydoc.docx", "rb") as f:
      elements = partition(file=f)


.. code:: python

  from unstructured.partition.auto import partition

  elements = partition(filename="example-docs/layout-parser-paper-fast.pdf")


``partition_docx``
------------------

The ``partition_docx`` partitioning brick pre-processes Microsoft Word documents
saved in the ``.docx`` format. This staging brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_docx`` can take a filename or file-like object
as input, as shown in the two examples below.

Examples:

.. code:: python

  import docx

  from unstructured.partition.docx import partition_docx

  document = docx.Document()
  document.add_paragraph("Important Analysis", style="Heading 1")
  document.add_paragraph("Here is my first thought.", style="Body Text")
  document.add_paragraph("Here is my second thought.", style="Normal")
  document.save("mydoc.docx")

  elements = partition_docx(filename="mydoc.docx")

  with open("mydoc.docx", "rb") as f:
      elements = partition_docx(file=f)

``partition_pptx``
---------------------

The ``partition_pptx`` partitioning brick pre-processes Microsoft PowerPoint documents
saved in the ``.pptx`` format. This staging brick uses a combination of the styling
information in the document and the structure of the text to determine the type
of a text element. The ``partition_pptx`` can take a filename or file-like object
as input, as shown in the two examples below.

Examples:

.. code:: python

  from unstructured.partition.pptx import partition_pptx

  elements = partition_pptx(filename="example-docs/fake-power-point.pptx")

  with open("example-docs/fake-power-point.pptx", "rb") as f:
      elements = partition_pptx(file=f)


``partition_html``
---------------------

The ``partition_html`` function partitions an HTML document and returns a list
of document ``Element`` objects. ``partition_html`` can take a filename, file-like
object, or string as input. The three examples below all produce the same output.

Examples:

.. code:: python

  from unstructured.partition.html import partition_html

  elements = partition_html(filename="example-docs/example-10k.html")

  with open("example-docs/example-10k.html", "r") as f:
      elements = partition_html(file=f)

  with open("example-docs/example-10k.html", "r") as f:
      text = f.read()
  elements = partition_html(text=text)


``partition_pdf``
---------------------

The ``partition_pdf`` function segments a PDF document by using a document image analysis model.
If you set ``url=None``, the document image analysis model will execute locally. You need to install ``unstructured[local-inference]``
if you'd like to run inference locally.
If you set the URL, ``partition_pdf`` will make a call to a remote inference server.
``partition_pdf`` also includes a ``token`` function that allows you to pass in an authentication
token for a remote API call.

Examples:

.. code:: python

  from unstructured.partition.pdf import partition_pdf

  # Returns a List[Element] present in the pages of the parsed pdf document
  elements = partition_pdf("example-docs/layout-parser-paper-fast.pdf", url=None)


``partition_image``
---------------------

The ``partition_image`` function has the same API as ``partition_pdf``, which is document above.
The only difference is that ``partition_image`` does not need to convert a PDF to an image
prior to processing. The ``partition_image`` function supports ``.png`` and ``.jpg`` files.

Examples:

.. code:: python

  from unstructured.partition.image import partition_image

  # Returns a List[Element] present in the pages of the parsed image document
  elements = partition_image("example-docs/layout-parser-paper-fast.jpg", url=None)



``partition_email``
---------------------

The ``partition_email`` function partitions ``.eml`` documents and works with exports
from email clients such as Microsoft Outlook and Gmail. The ``partition_email``
takes a filename, file-like object, or raw text as input and produces a list of
document ``Element`` objects as output. Also ``content_source`` can be set to ``text/html``
(default) or ``text/plain`` to process the html or plain text version of the email, respectively.
In order for ``partition_email`` to also return the header information (e.g. sender, recipient,
attachment, etc.), ``include_headers`` must be set to ``True``. Returns tuple with body elements
first and header elements second, if ``include_headers`` is True.

Examples:

.. code:: python

  from unstructured.partition.email import partition_email

  elements = partition_email(filename="example-docs/fake-email.eml")

  with open("example-docs/fake-email.eml", "r") as f:
      elements = partition_email(file=f)

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text)

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text, content_source="text/plain")

  with open("example-docs/fake-email.eml", "r") as f:
      text = f.read()
  elements = partition_email(text=text, include_headers=True)


``partition_text``
---------------------

The ``partition_text`` function partitions text files. The ``partition_text``
takes a filename, file-like object, and raw text as input and produces ``Element`` objects as output.

Examples:

.. code:: python

  from unstructured.partition.text import partition_text

  elements = partition_text(filename="example-docs/fake-text.txt")

  with open("example-docs/fake-text.txt", "r") as f:
    elements = partition_text(file=f)

  with open("example-docs/fake-text.txt", "r") as f:
    text = f.read()
  elements = partition_text(text=text)


``extract_attachment_info``
----------------------------

The ``extract_attachment_info`` function takes an ``email.message.Message`` object
as input and returns the a list of dictionaries containing the attachment information,
such as ``filename``, ``size``, ``payload``, etc. The attachment is saved to the ``output_dir``
if specified.

.. code:: python

  import email
  from unstructured.partition.email import extract_attachment_info

  with open("example-docs/fake-email-attachment.eml", "r") as f:
      msg = email.message_from_file(f)
  attachment_info = extract_attachment_info(msg, output_dir="example-docs")


``is_bulleted_text``
----------------------

Uses regular expression patterns to check if a snippet of text is a bullet point. Only
triggers if the bullet point appears at the start of the snippet.

Examples:

.. code:: python

  from unstructured.partition.text_type import is_bulleted_text

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
* Narrative text must contain at least one English word (if ``language`` is set to "en")
* Text that exceeds the specified caps ratio cannot be narrative text. The threshold
  is configurable with the ``cap_threshold`` kwarg. To ignore this check, you can set
  ``cap_threshold=1.0``. You can also set the threshold by using the
  ``UNSTRUCTURED_NARRATIVE_TEXT_CAP_THRESHOLD`` environment variable. The environment variable
  takes precedence over the kwarg.
* If a the text contains too many non-alpha characters it is
  not narrative text.
  The default is to expect a minimum of 50% alpha characters
  (not countings spaces). You can change the minimum value with the
  ``non_alpha_ratio`` kwarg or the ``UNSTRUCTURED_NARRATIVE_TEXT_NON_ALPHA_RATIO`` environment variable.
  The environment variables takes precedence over the kwarg.
* The cap ratio test does not apply to text that is all uppercase.


Examples:

.. code:: python

  from unstructured.partition.text_type import is_possible_narrative_text

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
* Text that is all numeric cannot be a title.
* If a title contains too many words it is not a title. The default max length is ``12``. You can change the max length with
  the ``title_max_word_length`` kwarg or the ``UNSTRUCTURED_TITLE_MAX_WORD_LENGTH`` environment variable. The environment
  variable takes precedence over the kwarg.
* If a text contains too many non-alpha characters it is not a
  title. The default is to expect a minimum of 50% alpha characters
  (not countings spaces). You can change the minimum value with the
  ``non_alpha_ratio`` kwarg or the ``UNSTRUCTURED_TITLE_NON_ALPHA_RATIO`` environment variable.
  The environment variables takes precedence over the kwarg.
* Narrative text must contain at least one English word (if ``language`` is set to "en")
* If a title contains more than one sentence that exceeds a certain length, it cannot be a title. Sentence length threshold is controlled by the ``sentence_min_length`` kwarg and defaults to 5.
* If a segment of text ends in a comma, it is not considered a potential title. This is to avoid salutations like "To My Dearest Friends," getting flagged as titles.


Examples:

.. code:: python

  from unstructured.partition.text_type import is_possible_title

  # Returns True because the text passes all the tests
  example_2 = "ITEM 1A. RISK FACTORS"
  is_possible_title(example_2)

  # Returns True because there is only one sentence
  example_2 = "Make sure you brush your teeth before you go to bed."
  is_possible_title(example_2, sentence_min_length=5)

  # Returns False because there are two sentences
  example_3 = "Make sure you brush your teeth. Do it before you go to bed."
  is_possible_title(example_3, sentence_min_length=5)


``contains_us_phone_number``
----------------------------

Checks to see if a section of text contains a US phone number.

Examples:

.. code:: python

  from unstructured.partition.text_type import contains_us_phone_number

  # Returns True because the text includes a phone number
  contains_us_phone_number("Phone number: 215-867-5309")


``contains_verb``
-----------------

Checks if the text contains a verb. This is used in ``is_possible_narrative_text``, but can
be used independently as well. The function identifies verbs using the NLTK part of speech
tagger. Text that is all upper case is lower cased before part of speech detection. This is
because the upper case letters sometimes cause the part of speech tagger to miss verbs.
The following part of speech tags are identified as verbs:

* ``VB``
* ``VBG``
* ``VBD``
* ``VBN``
* ``VBP``
* ``VBZ``

Examples:

.. code:: python

  from unstructured.partition.text_type import contains_verb

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

  from unstructured.partition.text_type import sentence_count

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
defaults to ``0.3``. Only runs on sections of text that are a single sentence. The caps ratio check does not apply to text that is all capitalized.

Examples:

.. code:: python

  from unstructured.partition.text_type import exceeds_cap_ratio

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
  clean("ITEM 1A:     RISK-FACTORS", extra_whitespace=True, dashes=True)


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


``clean_ordered_bullets``
-------------------------

Remove alpha-numeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_ordered_bullets

  # Returns "This is a very important point"
  clean_bullets("1.1 This is a very important point")

  # Returns "This is a very important point ●"
  clean_bullets("a.b This is a very important point ●")


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
  remove_punctuation("“A lovely quote!”")


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

  # Returns "This is the best summary of all time!"
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

  # Returns "The end!"
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

  # Returns "Here I am!"
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

  # Returns "Look at me, I'm flying!"
  extract_text_after(text, r"SPEAKER \d{1}:")

``extract_email_address``
--------------------------

Extracts email addresses from a string input and returns a list of all the email
addresses in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_email_address

  text = """Me me@email.com and You <You@email.com>
      ([ba23::58b5:2236:45g2:88h2]) (10.0.2.01)"""

  # Returns "['me@email.com', 'you@email.com']"
  extract_email_address(text)


``extract_ip_address``
------------------------

Extracts IPv4 and IPv6 IP addresses in the input string and
returns a list of all IP address in input string.

.. code:: python

  from unstructured.cleaners.extract import extract_ip_address

  text = """Me me@email.com and You <You@email.com>
    ([ba23::58b5:2236:45g2:88h2]) (10.0.2.01)"""

  # Returns "['ba23::58b5:2236:45g2:88h2', '10.0.2.01']"
  extract_ip_address(text)


``extract_ip_address_name``
----------------------------

Extracts the names of each IP address in the ``Received`` field(s) from an ``.eml``
file. ``extract_ip_address_name`` takes in a string and returns a list of all
IP addresses in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_ip_address_name

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns "['ABC.DEF.local', 'ABC.DEF.local2']"
  extract_ip_address_name(text)


``extract_mapi_id``
----------------------

Extracts the ``mapi id`` in the ``Received`` field(s) from an ``.eml``
file. ``extract_mapi_id`` takes in a string and returns a list of a string
containing the ``mapi id`` in the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_mapi_id

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns "['32.88.5467.123']"
  extract_mapi_id(text)


``extract_datetimetz``
----------------------

Extracts the date, time, and timezone in the ``Received`` field(s) from an ``.eml``
file. ``extract_datetimetz`` takes in a string and returns a datetime.datetime
object from the input string.

.. code:: python

  from unstructured.cleaners.extract import extract_datetimetz

  text = """from ABC.DEF.local ([ba23::58b5:2236:45g2:88h2]) by
    \n ABC.DEF.local2 ([ba23::58b5:2236:45g2:88h2%25]) with mapi id\
    n 32.88.5467.123; Fri, 26 Mar 2021 11:04:09 +1200"""

  # Returns datetime.datetime(2021, 3, 26, 11, 4, 9, tzinfo=datetime.timezone(datetime.timedelta(seconds=43200)))
  extract_datetimetz(text)


``extract_us_phone_number``
---------------------------

Extracts a phone number from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_us_phone_number

  # Returns "215-867-5309"
  extract_us_phone_number("Phone number: 215-867-5309")


``extract_ordered_bullets``
---------------------------

Extracts alpha-numeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_ordered_bullets

  # Returns ("1", "1", None)
  extract_ordered_bullets("1.1 This is a very important point")

  # Returns ("a", "1", None)
  extract_ordered_bullets("a.1 This is a very important point")


``translate_text``
------------------

The ``translate_text`` cleaning bricks translates text between languages. ``translate_text``
uses the `Helsinki NLP MT models <https://huggingface.co/Helsinki-NLP>`_ from
``transformers`` for machine translation. Works for Russian, Chinese, Arabic, and many
other languages.

Parameters:

* ``text``: the input string to translate.
* ``source_lang``: the two letter language code for the source language of the text.
  If ``source_lang`` is not specified,
  the language will be detected using ``langdetect``.
* ``target_lang``: the two letter language code for the target language for translation.
  Defaults to ``"en"``.


Examples:

.. code:: python

  from unstructured.cleaners.translate import translate_text

  # Output is "I'm a Berliner!"
  translate_text("Ich bin ein Berliner!")

  # Output is "I can also translate Russian!"
  translate_text("Я тоже можно переводать русский язык!", "ru", "en")


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

  # elements will look like:
  # [ Title(text="My Title"), NarrativeText(text="My Narrative")]
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

  # The resulting CSV file is ready to be used with Prodigy
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

  from unstructured.documents.elements import Text
  from unstructured.staging.datasaur import stage_for_datasaur

  elements  = [Text("Text1"),Text("Text2")]
  datasaur_data = stage_for_datasaur(elements)

The output is a list of dictionaries, each one with two keys:
"text" with the content of the element and
"entities" with an empty list.

You can also specify specify entities in the ``stage_for_datasaur`` brick. Entities
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


``stage_for_argilla``
--------------------------

Convert a list of ``Text`` elements to an `Argilla Dataset <https://docs.argilla.io/en/latest/reference/python/python_client.html#python-ref-datasets>`_.
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
