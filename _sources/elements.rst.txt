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
