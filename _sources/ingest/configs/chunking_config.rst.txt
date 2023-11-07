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
* ``chunk_elements (default False)``: Boolean flag whether to run chunking as part of the ingest process.
* ``multipage_sections (default True)``: If True, sections can span multiple pages.
* ``combine_text_under_n_chars (default 500)``: Combines elements (for example a series of titles) until a section reaches a length of n characters. Defaults to `max_characters` which combines chunks whenever space allows. Specifying 0 for this argument suppresses combining of small chunks. Note this value is "capped" at the `new_after_n_chars` value since a value higher than that would not change this parameter's effect.
* ``max_characters (default 1500)``: Chunks elements text and text_as_html (if present) into chunks of length n characters (hard max)
