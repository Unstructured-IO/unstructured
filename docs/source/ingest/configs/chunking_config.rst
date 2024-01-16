Chunking Configuration
=========================

A common chunking configuration is a critical element in the data processing pipeline, particularly
when creating embeddings and populating vector databases with the results. This configuration defines
the parameters governing the segmentation of text into meaningful chunks, whether at the document,
paragraph, or sentence level. It plays a pivotal role in determining the size and structure of these chunks,
ensuring that they align with the specific requirements of downstream tasks, such as embedding generation and
vector database population. By carefully configuring chunking parameters, users can optimize the granularity of
data segments, ultimately contributing to more cohesive and contextually rich results. This is crucial for tasks
like natural language processing and text analysis, as well as for the efficient storage and retrieval of embeddings
in vector databases, enhancing the quality and relevance of the results.

Configs
---------------------
* ``chunk_elements (default False)``: (Deprecated) Boolean flag whether to run chunking as part of
  the ingest process. This option is deprecated in favor of the ``chunking_strategy`` option. This
  option being set True has the same effect as ``chunking_strategy=by_title``.
* ``chunking_strategy``: One of "basic" or "by_title". When omitted, no chunking is performed. The
  "basic" strategy maximally fills each chunk with whole elements, up the specified size limits
  (``max_characters`` and ``new_after_n_chars`` described below). A single element that exceeds this
  length is divided into two or more chunks using text-splitting. A ``Table`` element is never
  combined with any other element and appears as a chunk of its own or as a sequence of
  ``TableChunk`` elements splitting is required. The "by_title" behaviors are the same except that
  section and optionally page boundaries are respected such that two consecutive elements from
  different sections appear in separate chunks.
* ``multipage_sections (default True)``: When False, in addition to section boundaries, page
  boundaries are also respected. Only operative for the "by_title" strategy.
* ``combine_text_under_n_chars (default 500)``: Combines elements (for example a series of titles) until a section reaches a length of n characters. Defaults to `max_characters` which combines chunks whenever space allows. Specifying 0 for this argument suppresses combining of small chunks. Note this value is "capped" at the `new_after_n_chars` value since a value higher than that would not change this parameter's effect.
* ``new_after_n_chars (default 1500)``: Cuts off new sections once they reach a length of n characters (soft max). Defaults to `max_characters` when not specified, which effectively disables any soft window. Specifying 0 for this argument causes each element to appear in a chunk by itself (although an element with text longer than `max_characters` will be still be split into two or more chunks).
* ``max_characters (default 1500)``: Chunks elements text and text_as_html (if present) into chunks of length n characters (hard max)
