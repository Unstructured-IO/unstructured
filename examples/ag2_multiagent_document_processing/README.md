# AG2 Multi-Agent Document Processing with Unstructured

This example demonstrates how to use [AG2](https://ag2.ai/) (formerly AutoGen)
multi-agent conversations with [Unstructured](https://unstructured.io/) for
intelligent document processing and analysis.

## Overview

Two AG2 agents collaborate to process and analyze documents:

- **Document Agent** -- Uses Unstructured to partition documents and extract
  structured elements (text, tables, titles, narrative)
- **Analyst Agent** -- Analyzes the extracted content, answers questions,
  and produces summaries with source references

## Prerequisites

- Python >= 3.11
- OpenAI API key
- System dependencies: `libmagic-dev`, `poppler-utils`, `tesseract-ocr` (for PDF/image support)

## Quick Start

```bash
# Install dependencies
pip install "unstructured[all-docs]" "ag2[openai]>=0.11.4,<1.0"

# Set API key
export OPENAI_API_KEY="your-api-key"

# Run the example (uses sample docs from example-docs/)
python run.py

# Or specify your own document
python run.py --file /path/to/your/document.pdf
```

## How It Works

1. **Unstructured** partitions a document into structured elements
   (Title, NarrativeText, Table, ListItem, etc.)
2. **AG2 Document Agent** wraps Unstructured as a registered tool, callable by agents
3. **AG2 Analyst Agent** receives extracted elements and produces analysis
4. Agents collaborate via AG2 GroupChat with automatic tool execution

## Tech Stack

- [AG2](https://ag2.ai/) -- Multi-agent conversation framework (500K+ monthly PyPI downloads)
- [Unstructured](https://unstructured.io/) -- Document ETL for LLMs (25+ file types)
