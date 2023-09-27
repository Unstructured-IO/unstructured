########
Chunking
########

Chunking functions in ``unstructured`` use metadata and document elements
detected with ``partition`` functions to split a document into subsections
for uses cases such as Retrieval Augmented Generation (RAG).


``chunk_by_title``
------------------

The ``chunk_by_title`` function combines elements into sections by looking
for the presence of titles. When a title is detected, a new section is created.
Tables and non-text elements (such as page breaks or images) are always their
own section.

New sections are also created if changes in metadata occure. Examples of when
this occurs include when the section of the document or the page number changes
or when an element comes from an attachment instead of from the main document.
If you set ``multipage_sections=True``, ``chunk_by_title`` will allow for sections
that span between pages. This kwarg is ``True`` by default.

``chunk_by_title`` will start a new section if the length of a section exceed
``new_after_n_chars``. The default value is ``1500``. ``chunk_by_title`` does
not split elements, it is possible for a section to exceed that lenght, for
example if a ``NarrativeText`` elements exceeds ``1500`` characters on its on.

Similarly, sections under ``combine_under_n_chars`` will be combined if they
do not exceed the specified threshold, which defaults to ``500``. This will combine
a series of ``Title`` elements that occur one after another, which sometimes
happens in lists that are not detected as ``ListItem`` elements. Set
``combine_under_n_chars=0`` to turn off this behavior.

The following shows an example of how to use ``chunk_by_title``. You will
see the document chunked into sections instead of elements.


.. code:: python

  from unstructured.partition.html import partition_html
  from unstructured.chunking.title import chunk_by_title

  url = "https://understandingwar.org/backgrounder/russian-offensive-campaign-assessment-august-27-2023-0"
  elements = partition_html(url=url)
  chunks = chunk_by_title(elements)

  for chunk in chunks:
      print(chunk)
      print("\n\n" + "-"*80)
      input()
