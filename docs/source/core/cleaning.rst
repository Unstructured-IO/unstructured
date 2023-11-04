
########
Cleaning
########


As part of data preparation for an NLP model, it's common to need to clean up your data prior to passing it into the model.
If there's unwanted content in your output, for example, it could impact the quality of your NLP model.
To help with this, the ``unstructured`` library includes cleaning functions to help users sanitize output before sending it to downstream applications.


Some cleaning functions apply automatically.
In the example in the **Partition** section, the output ``Philadelphia Eaglesâ\x80\x99 victory`` automatically gets converted to ``Philadelphia Eagles' victory`` in ``partition_html`` using the ``replace_unicode_quotes`` cleaning function.
You can see how that works in the code snippet below:

.. code:: python

  from unstructured.cleaners.core import replace_unicode_quotes

  replace_unicode_quotes("Philadelphia Eaglesâ\x80\x99 victory")



Document elements in ``unstructured`` include an ``apply`` method that allow you to apply the text cleaning to the document element without instantiating a new element.
The ``apply`` method expects a callable that takes a string as input and produces another string as output.
In the example below, we invoke the ``replace_unicode_quotes`` cleaning function using the ``apply`` method.


.. code:: python

  from unstructured.documents.elements import Text

  element = Text("Philadelphia Eaglesâ\x80\x99 victory")
  element.apply(replace_unicode_quotes)
  print(element)


Since a cleaning function is just a ``str -> str`` function, users can also easily include their own cleaning functions for custom data preparation tasks.
In the example below, we remove citations from a section of text.


.. code:: python

  import re

  remove_citations = lambda text: re.sub("\[\d{1,3}\]", "", text)

  element = Text("[1] Geolocated combat footage has confirmed Russian gains in the Dvorichne area northwest of Svatove.")
  element.apply(remove_citations)
  print(element)


See below for a full list of cleaning functions in the ``unstructured`` library.


``bytes_string_to_string``
---------------------------

Converts an output string that looks like a byte string to a string using the specified encoding. This
happens sometimes in ``partition_html`` when there is a character like an emoji that isn't expected
by the HTML parser. In that case, the encoded bytes get processed.

Examples:

.. code:: python

  from unstructured.cleaners.core import bytes_string_to_string

  text = "Hello ð\x9f\x98\x80"
  # The output should be "Hello 😀"
  bytes_string_to_string(text, encoding="utf-8")


.. code:: python

  from unstructured.cleaners.core import bytes_string_to_string
  from unstructured.partition.html import partition_html

  text = """\n<html charset="utf-8"><p>Hello 😀</p></html>"""
  elements = partition_html(text=text)
  elements[0].apply(bytes_string_to_string)
  # The output should be "Hello 😀"
  elements[0].text

For more information about the ``bytes_string_to_string`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


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

For more information about the ``clean`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


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

For more information about the ``clean_bullets`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_dashes``
----------------

Removes dashes from a section of text. Also handles special characters
such as ``\u2013``.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_dashes

  # Returns "ITEM 1A: RISK FACTORS"
  clean_dashes("ITEM 1A: RISK-FACTORS\u2013")

For more information about the ``clean_dashes`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_extra_whitespace``
--------------------------

Removes extra whitespace from a section of text. Also handles special characters
such as ``\xa0`` and newlines.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_extra_whitespace

  # Returns "ITEM 1A: RISK FACTORS"
  clean_extra_whitespace("ITEM 1A:     RISK FACTORS\n")

For more information about the ``clean_extra_whitespace`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_non_ascii_chars``
-------------------------

Removes non-ascii characters from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_non_ascii_chars

  text = "\x88This text contains®non-ascii characters!●"

  # Returns "This text containsnon-ascii characters!"
  clean_non_ascii_chars(text)

For more information about the ``clean_non_ascii_chars`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_ordered_bullets``
-------------------------

Remove alphanumeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_ordered_bullets

  # Returns "This is a very important point"
  clean_bullets("1.1 This is a very important point")

  # Returns "This is a very important point ●"
  clean_bullets("a.b This is a very important point ●")

For more information about the ``clean_ordered_bullets`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


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

For more information about the ``clean_postfix`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


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

For more information about the ``clean_prefix`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``clean_trailing_punctuation``
-------------------------------

Removes trailing punctuation from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.core import clean_trailing_punctuation

  # Returns "ITEM 1A: RISK FACTORS"
  clean_trailing_punctuation("ITEM 1A: RISK FACTORS.")

For more information about the ``clean_trailing_punctuation`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``group_broken_paragraphs``
---------------------------

Groups together paragraphs that are broken up with line breaks
for visual or formatting purposes. This is common in ``.txt`` files.
By default, ``group_broken_paragraphs`` groups together lines split
by ``\n``. You can change that behavior with the ``line_split``
kwarg. The function considers ``\n\n`` to be a paragraph break by
default. You can change that behavior with the ``paragraph_split`` kwarg.

Examples:

.. code:: python

  from unstructured.cleaners.core import group_broken_paragraphs

  text = """The big brown fox
  was walking down the lane.

  At the end of the lane, the
  fox met a bear."""

  group_broken_paragraphs(text)

.. code:: python

  import re
  from unstructured.cleaners.core import group_broken_paragraphs

  para_split_re = re.compile(r"(\s*\n\s*){3}")

  text = """The big brown fox

  was walking down the lane.


  At the end of the lane, the

  fox met a bear."""

  group_broken_paragraphs(text, paragraph_split=para_split_re)

For more information about the ``group_broken_paragraphs`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


``remove_punctuation``
--------------------------

Removes ASCII and unicode punctuation from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import remove_punctuation

  # Returns "A lovely quote"
  remove_punctuation("“A lovely quote!”")

For more information about the ``remove_punctuation`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`_.


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

For more information about the ``replace_unicode_quotes`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`__.


``translate_text``
------------------

The ``translate_text`` cleaning functions translates text between languages. ``translate_text``
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

For more information about the ``translate_text`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/translate.py>`__.
