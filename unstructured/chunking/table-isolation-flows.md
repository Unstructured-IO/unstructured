# Table Isolation Flow Before and After #4307

This note captures how chunking flow changed when table-family isolation moved earlier in the
pipeline in PR #4307.

Scenario used in both diagrams:

- Input element order: `NarrativeText("intro text")`, `Table(...)`, `NarrativeText("tail text")`.
- Shared call path: `partition_*()` -> `chunk_by_title()` or `chunk_elements()` ->
  `PreChunker.iter_pre_chunks()` -> `PreChunk.iter_chunks()`.

## Before #4307 (table leakage possible)

```mermaid
flowchart TD
    A["partition_*() with chunking strategy"] --> B["chunk_by_title() or chunk_elements()"]
    B --> C["PreChunker.iter_pre_chunks()"]
    C --> D["PreChunkBuilder (pre-#4307): will_fit checked only size/soft-max limits"]
    D --> E["Sequence processed: Text intro -> Table -> Text tail"]
    E --> F["A mixed pre-chunk could form: [Text, Table, Text]"]
    F --> G["PreChunkCombiner could also merge table-containing and text pre-chunks"]
    G --> H{"PreChunk.iter_chunks() route"}
    H -->|not a single-table pre-chunk| I["_Chunker"]
    I --> J["CompositeElement chunk(s), table text flattened into narrative chunk text"]
    H -->|single-table pre-chunk only| K["_TableChunker"]
    K --> L["Table or TableChunk"]
```

## After #4307 (early table-family isolation)

```mermaid
flowchart TD
    A["partition_*() with chunking strategy"] --> B["chunk_by_title() or chunk_elements()"]
    B --> C["PreChunker.iter_pre_chunks()"]
    C --> D["PreChunkBuilder (post-#4307) table-family guards"]
    D --> E{"Trying to place a table-family element?"}
    E -->|yes and pre-chunk non-empty| F["will_fit = False, flush current text pre-chunk first"]
    F --> G["Start table-only pre-chunk: [Table]"]
    E -->|no and current pre-chunk already has table-family| H["will_fit = False, flush table pre-chunk"]
    H --> I["Start next text pre-chunk"]
    G --> J["Pre-chunk boundaries become: [Text] [Table] [Text]"]
    I --> J
    J --> K["PreChunk.can_combine() rejects table<->text side-by-side merges"]
    K --> L{"PreChunk.iter_chunks() route"}
    L -->|text-only pre-chunk| M["_Chunker -> CompositeElement"]
    L -->|single table-family pre-chunk| N["_TableChunker -> Table or TableChunk(s)"]
    M --> O["Output types preserve table boundary"]
    N --> O
```

## Command-backed observed output types

| Revision | `chunk_elements([Text, Table, Text])` types | `partition_html(..., chunking_strategy=\"by_title\")` types |
| --- | --- | --- |
| pre-#4307 base (`47f4728`) | `["CompositeElement"]` | `["CompositeElement"]` |
| post-#4307 fix (`547d3c8`) | `["CompositeElement", "Table", "CompositeElement"]` | `["CompositeElement", "Table", "CompositeElement"]` |

Code touchpoints for this behavior are in `unstructured/chunking/base.py`:
`PreChunkBuilder.will_fit()` and `PreChunk.can_combine()`.
