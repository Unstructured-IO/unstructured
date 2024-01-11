########
Chunking
########

Chunking functions in ``unstructured`` use metadata and document elements detected with
``partition`` functions to split a document into smaller parts for uses cases such as Retrieval
Augmented Generation (RAG).

Chunking Basics
---------------

Chunking in ``unstructured`` differs from other chunking mechanisms you may be familiar with.
Typical approaches start with the text extracted from the document and form chunks based on
plain-text features, character sequences like ``"\n\n"`` or ``"\n"`` that might indicate a paragraph
boundary or list-item boundary.

Because ``unstructured`` uses specific knowledge about each document format to partition the
document into semantic units (document elements), we only need to resort to text-splitting when a
single element exceeds the desired maximum chunk size. Except in that case, all chunks contain one
or more whole elements, preserving the coherence of semantic units established during partitioning.

A few concepts about chunking are worth introducing before discussing the details.

- Chunking is performed on *document elements*. It is a separate step performed *after*
  partitioning, on the elements produced by partitioning. (Although it can be combined with
  partitioning in a single step.)

- In general, chunking *combines* consecutive elements to form chunks as large as possible without
  exceeding the maximum chunk size.

- A single element that by itself exceeds the maximum chunk size is divided into two or more chunks
  using text-splitting.

- Chunking produces a sequence of ``CompositeElement``, ``Table``, or ``TableChunk`` elements. Each
  "chunk" is an instance of one of these three types.


Chunking Options
----------------

The following options are available to tune chunking behaviors. These are keyword arguments that can
be used in a partitioning or chunking function call. All these options have defaults and need only
be specified when a non-default setting is required. Specific chunking strategies (such as
"by-title") may have additional options.

- ``max_characters: int (default=500)`` - the hard maximum size for a chunk. No chunk will exceed
  this number of characters. A single element that by itself exceeds this size will be divided into
  two or more chunks using text-splitting.

- ``new_after_n_chars: int (default=max_characters)`` - the "soft" maximum size for a chunk. A chunk
  that already exceeds this number of characters will not be extended, even if the next element
  would fit without exceeding the specified hard maximum. This can be used in conjunction with
  ``max_characters`` to set a "preferred" size, like "I prefer chunks of around 1000 characters, but
  I'd rather have a chunk of 1500 (max_characters) than resort to text-splitting". This would be
  specified with ``(..., max_characters=1500, new_after_n_chars=1000)``.

- ``overlap: int (default=0)`` - only when using text-splitting to break up an oversized chunk,
  include this number of characters from the end of the prior chunk as a prefix on the next. This
  can mitigate the effect of splitting the semantic unit represented by the oversized element at an
  arbitrary position based on text length.

- ``overlap_all: bool (default=False)`` - also apply overlap between "normal" chunks, not just when
  text-splitting to break up an oversized element. Because normal chunks are formed from whole
  elements that each have a clean semantic boundary, this option may "pollute" normal chunks. You'll
  need to decide based on your use-case whether this option is right for you.


Chunking elements
-----------------

Chunking can be performed as part of partitioning or as a separate step after
partitioning:

Specifying a chunking strategy while partitioning
+++++++++++++++++++++++++++++++++++++++++++++++++

Chunking can be performed as part of partitioning by specifying a value for the
``chunking_strategy`` argument. The current options are ``basic`` and ``by-title`` (described
below).

.. code:: python

  from unstructured.partition.html import partition_html

  chunks = partition_html(url=url, chunking_strategy="basic")

Calling a chunking function
+++++++++++++++++++++++++++

Chunking can also be performed separately from partitioning by calling a chunking function directly.
This may be convenient, for example, when tuning chunking parameters. Chunking is typically faster
than partitioning, especially when OCR or inference is used, so a faster feedback loop is possible
by doing these separately:

.. code:: python

  from unstructured.chunking.basic import chunk_elements
  from unstructured.partition.html import partition_html

  url = "https://understandingwar.org/backgrounder/russian-offensive-campaign-assessment-august-27-2023-0"
  elements = partition_html(url=url)
  chunks = chunk_elements(elements)

  # -- OR --

  from unstructured.chunking.title import chunk_by_title

  chunks = chunk_by_title(elements)

  for chunk in chunks:
      print(chunk)
      print("\n\n" + "-"*80)
      input()


Chunking Strategies
-------------------

There are currently two chunking strategies, *basic* and *by_title*. The ``by_title`` strategy
shares most behaviors with the basic strategy so we'll describe the baseline strategy first:

"basic" chunking strategy
+++++++++++++++++++++++++

- The basic strategy combines sequential elements to maximally fill each chunk while respecting both
  the specified ``max_characters`` (hard-max) and ``new_after_n_chars`` (soft-max) option values.

- A single element that by itself exceeds the hard-max is isolated (never combined with another
  element) and then divided into two or more chunks using text-splitting.

- A ``Table`` element is always isolated and never combined with another element. A ``Table`` can be
  oversized, like any other text element, and in that case is divided into two or more
  ``TableChunk`` elements using text-splitting.

- If specified, ``overlap`` is applied between split-chunks and is also applied between normal
  chunks when ``overlap_all`` is ``True``.


"by_title" chunking strategy
++++++++++++++++++++++++++++

The ``by_title`` chunking strategy preserves section boundaries and optionally page boundaries as
well. "Preserving" here means that a single chunk will never contain text that occurred in two
different sections. When a new section starts, the existing chunk is closed and a new one started,
even if the next element would fit in the prior chunk.

In addition to the behaviors of the ``basic`` strategy above, the ``by_title`` strategy has the
following behaviors:

- **Detect section headings.** A ``Title`` element is considered to start a new section. When a
  ``Title`` element is encountered, the prior chunk is closed and a new chunk started, even if the
  ``Title`` element would fit in the prior chunk. This implements the first aspect of the "preserve
  section boundaries" contract.

- **Detect metadata.section change.** An element with a new value in ``element.metadata.section`` is
  considered to start a new section. When a change in this value is encountered a new chunk is
  started. This implements the second aspect of preserving section boundaries. This metadata is not
  present in all document formats so is not used alone. An element having ``None`` for this metadata
  field is considered to be part of the prior section; a section break is only detected on an
  explicit change in value.

- **Respect page boundaries.** Page boundaries can optionally also be respected using the
  ``multipage_sections`` argument. This defaults to ``True`` meaning that a page break does *not*
  start a new chunk. Setting this to ``False`` will separate elements that occur on different pages
  into distinct chunks.

- **Combine small sections.** In certain documents, partitioning may identify a list-item or other
  short paragraph as a ``Title`` element even though it does not serve as a section heading. This
  can produce chunks substantially smaller than desired. This behavior can be mitigated using the
  ``combine_text_under_n_chars`` argument. This defaults to the same value as ``max_characters``
  such that sequential small sections are combined to maximally fill the chunking window. Setting
  this to ``0`` will disable section combining.
