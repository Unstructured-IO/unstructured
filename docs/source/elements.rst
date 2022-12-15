Elements
--------

The following are the structured page elements that are available within the ``unstructured``
package. Partioning bricks convert raw documents to this common set of elements. If you need
a custom element, the recommended approach is to create a sub-class of one of the default
elements.

* ``Page`` - A collection of elements on the same page of a document.
* ``Text`` - A block of text within a document.
* ``NarrativeText`` - Sections of a document that include well-formed prose. Sub-class of ``Text``.
* ``Title`` - Headings and sub-headings wtihin a document. Sub-class of ``Text``.
* ``ListItem`` - A text element that is part of an ordered or unordered list. Sub-class of ``Text``.


#########################################
Applying Cleaning Bricks to Text Elements
#########################################

You can apply cleaning bricks to a text element by using the ``apply`` method. The
apply method accepts any function that takes a string as input and produces a string
as output. Use the `partial` function from `functools` if you need to set additional
args or kwargs for your cleaning brick. The `apply` method will accept either a single
cleaner or a list of cleaners.

Examples:

.. code:: python

  from functools import partial

  from unstructured.cleaners.core import clean_prefix
  from unstructured.cleaners.translate import translate_text
  from unstructured.documents.elements import ListItem

  cleaners = [
    partial(clean_prefix, pattern=r"\[\d{1,2}\]"),
    partial(translate_text, target_lang="ru"),
  ]

  item = ListItem(text="[1] A Textbook on Crocodile Habitats")
  item.apply(cleaners)

  # The output will be: Учебник по крокодильным средам обитания
  print(item)