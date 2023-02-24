Elements
--------

The following are the structured page elements that are available within the ``unstructured``
package. Partitioning bricks convert raw documents to this common set of elements. If you need
a custom element, the recommended approach is to create a sub-class of one of the default
elements.

* ``Page`` - A collection of elements on the same page of a document.
* ``Text`` - A block of text within a document.
* ``NarrativeText`` - Sections of a document that include well-formed prose. Sub-class of ``Text``.
* ``Title`` - Headings and sub-headings wtihin a document. Sub-class of ``Text``.
* ``ListItem`` - A text element that is part of an ordered or unordered list. Sub-class of ``Text``.
* ``Address`` - A text item that consists only of an address. Sub-class of ``Text``.
* ``CheckBox`` - An element representing a check box. Has a ``checked`` element, which is a boolean indicating whether or not that box is checked.


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
  item.apply(*cleaners)

  # The output will be: Учебник по крокодильным средам обитания
  print(item)

####################
Serializing Elements
####################

The ``unstructured`` library includes helper functions for
reading and writing a list of ``Element`` objects to and
from JSON. You can use the following workflow for
serializing and deserializing an ``Element`` list.


.. code:: python

    from unstructured.documents.elements import ElementMetadata, Text, Title, FigureCaption
    from unstructured.staging.base import elements_to_json, elements_from_json

    filename = "my-elements.json"
    metadata = ElementMetadata(filename="fake-file.txt")
    elements = [
        FigureCaption(text="caption", metadata=metadata, element_id="1"),
        Title(text="title", metadata=metadata, element_id="2"),
        Text(text="title", metadata=metadata, element_id="3"),

    ]

    elements_to_json(elements, filename=filename)
    new_elements = elements_from_json(filename=filename)
