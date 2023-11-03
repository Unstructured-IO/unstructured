##########
Extracting
##########


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

For more information about the ``extract_datetimetz`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


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

For more information about the ``extract_email_address`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


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

For more information about the ``extract_ip_address`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


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

For more information about the ``extract_ip_address_name`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


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

For more information about the ``extract_mapi_id`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


``extract_ordered_bullets``
---------------------------

Extracts alphanumeric bullets from the beginning of text up to three “sub-section” levels.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_ordered_bullets

  # Returns ("1", "1", None)
  extract_ordered_bullets("1.1 This is a very important point")

  # Returns ("a", "1", None)
  extract_ordered_bullets("a.1 This is a very important point")

For more information about the ``extract_ordered_bullets`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


``extract_text_after``
----------------------

Extracts text that occurs after the specified pattern.

Options:

* If ``index`` is set, extract after the ``(index + 1)``\th occurrence of the pattern. The default is ``0``.
* Strips trailing whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_after

  text = "SPEAKER 1: Look at me, I'm flying!"

  # Returns "Look at me, I'm flying!"
  extract_text_after(text, r"SPEAKER \d{1}:")

For more information about the ``extract_text_after`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


``extract_text_before``
-----------------------

Extracts text that occurs before the specified pattern.

Options:

* If ``index`` is set, extract before the ``(index + 1)``\th occurrence of the pattern. The default is ``0``.
* Strips leading whitespace if ``strip`` is set to ``True``. The default is ``True``.


Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_text_before

  text = "Here I am! STOP Look at me! STOP I'm flying! STOP"

  # Returns "Here I am!"
  extract_text_before(text, r"STOP")

For more information about the ``extract_text_before`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


``extract_us_phone_number``
---------------------------

Extracts a phone number from a section of text.

Examples:

.. code:: python

  from unstructured.cleaners.extract import extract_us_phone_number

  # Returns "215-867-5309"
  extract_us_phone_number("Phone number: 215-867-5309")

For more information about the ``extract_us_phone_number`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/extract.py>`__.


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

For more information about the ``group_broken_paragraphs`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`__.


``remove_punctuation``
--------------------------

Removes ASCII and unicode punctuation from a string.

Examples:

.. code:: python

  from unstructured.cleaners.core import remove_punctuation

  # Returns "A lovely quote"
  remove_punctuation("“A lovely quote!”")

For more information about the ``remove_punctuation`` function, you can check the `source code here <https://github.com/Unstructured-IO/unstructured/blob/a583d47b841bdd426b9058b7c34f6aa3ed8de152/unstructured/cleaners/core.py>`__.


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

The ``translate_text`` cleaning function translates text between languages. ``translate_text``
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
