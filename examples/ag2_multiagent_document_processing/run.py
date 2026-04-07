"""AG2 Multi-Agent Document Processing with Unstructured.

This example demonstrates how AG2 (formerly AutoGen) multi-agent framework
can leverage Unstructured for intelligent document processing and analysis.

Two AG2 agents collaborate:
- **Document Agent**: Partitions documents using Unstructured, extracting
  structured elements (titles, narrative text, tables, list items, etc.)
- **Analyst Agent**: Analyzes extracted content, answers questions, and
  produces summaries with element-type awareness.

Requirements:
    pip install "unstructured[all-docs]" "ag2[openai]>=0.11.4,<1.0"

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/ag2_multiagent_document_processing/run.py
    python examples/ag2_multiagent_document_processing/run.py --file path/to/doc.pdf

AG2: https://ag2.ai/ | 500K+ monthly PyPI downloads
Unstructured: https://unstructured.io/ | 25+ document types
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from autogen import (
    AssistantAgent,
    GroupChat,
    GroupChatManager,
    LLMConfig,
    UserProxyAgent,
)

from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_dicts

# ---------------------------------------------------------------------------
# 1. Document processing functions using Unstructured
# ---------------------------------------------------------------------------


def partition_document(file_path: str) -> list[dict]:
    """Partition a document into structured elements using Unstructured.

    Args:
        file_path: Path to the document file.

    Returns:
        List of element dicts with type, text, and metadata.
    """
    elements = partition(filename=file_path)
    return elements_to_dicts(elements)


def format_elements_summary(elements: list[dict]) -> str:
    """Format extracted elements into a readable summary.

    Args:
        elements: List of element dicts from Unstructured.

    Returns:
        Formatted string with element types and content.
    """
    type_counts: dict[str, int] = {}
    for el in elements:
        el_type = el.get("type", "Unknown")
        type_counts[el_type] = type_counts.get(el_type, 0) + 1

    summary_parts = [
        f"Document contains {len(elements)} elements:",
        f"Element types: {json.dumps(type_counts, indent=2)}",
        "",
        "--- Extracted Content ---",
        "",
    ]

    for i, el in enumerate(elements, 1):
        el_type = el.get("type", "Unknown")
        text = el.get("text", "").strip()
        if text:
            summary_parts.append(f"[{i}] ({el_type}) {text[:500]}")
            if len(text) > 500:
                summary_parts.append(f"    ... (truncated, {len(text)} chars total)")
            summary_parts.append("")

    return "\n".join(summary_parts)


# ---------------------------------------------------------------------------
# 2. Find default sample document
# ---------------------------------------------------------------------------


def find_sample_document() -> str:
    """Find a sample document from the example-docs directory.

    Returns:
        Path to a sample document.

    Raises:
        FileNotFoundError: If no suitable sample document is found.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    example_docs = repo_root / "example-docs"

    if example_docs.exists():
        for pattern in ["layout-parser-paper.pdf", "example-10k.html", "*.pdf", "*.html"]:
            matches = list(example_docs.glob(pattern))
            if matches:
                return str(matches[0])

    raise FileNotFoundError(
        "No sample document found. Use --file to specify a document path, "
        "or run from the repository root where example-docs/ exists."
    )


# ---------------------------------------------------------------------------
# 3. AG2 agents with Unstructured tools
# ---------------------------------------------------------------------------


def main(file_path: Optional[str] = None) -> None:
    """Run the AG2 multi-agent document processing pipeline.

    Args:
        file_path: Optional path to a document. If None, uses a sample document.
    """
    if file_path is None:
        file_path = find_sample_document()

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Processing document: {file_path}")
    print(f"File size: {os.path.getsize(file_path):,} bytes")
    print()

    llm_config = LLMConfig(
        {
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "api_type": "openai",
        }
    )

    document_agent = AssistantAgent(
        name="document_agent",
        system_message=(
            "You are a document processing agent. When asked to process a document, "
            "use the process_document tool to extract structured content using "
            "Unstructured. Present the results clearly, noting the different element "
            "types found (Title, NarrativeText, Table, ListItem, etc.)."
        ),
        llm_config=llm_config,
    )

    analyst = AssistantAgent(
        name="analyst",
        system_message=(
            "You are a document analyst. Based on the extracted document content "
            "provided by the document_agent, produce a comprehensive analysis "
            "including: (1) document structure overview, (2) key topics and themes, "
            "(3) important facts or data points, (4) a concise executive summary. "
            "Reference specific element types and content. "
            "End with TERMINATE when done."
        ),
        llm_config=llm_config,
    )

    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        is_termination_msg=lambda x: bool(
            x.get("content", "") and "TERMINATE" in x.get("content", "")
        ),
    )

    @user_proxy.register_for_execution()
    @document_agent.register_for_llm(
        description=(
            "Process a document file using Unstructured to extract structured "
            "content elements. Supports PDF, HTML, Word, PowerPoint, email, "
            "images (with OCR), and 25+ other file types. Returns element types "
            "(Title, NarrativeText, Table, ListItem, etc.) with their text content."
        )
    )
    def process_document(document_path: str) -> str:
        """Process a document with Unstructured and return structured elements."""
        print(f"\n>>> [TOOL CALL] process_document('{document_path}')")
        print(">>> Partitioning document with Unstructured...")
        elements = partition_document(document_path)
        summary = format_elements_summary(elements)
        print(f">>> Extracted {len(elements)} elements")
        print(f">>> Summary length: {len(summary)} chars")
        print(">>> [TOOL DONE]\n")
        return summary

    @user_proxy.register_for_execution()
    @document_agent.register_for_llm(
        description=(
            "List the types of elements found in a document after processing. "
            "Useful for understanding document structure before deep analysis."
        )
    )
    def get_element_types(document_path: str) -> str:
        """Get a summary of element types in a document."""
        print(f"\n>>> [TOOL CALL] get_element_types('{document_path}')")
        print(">>> Scanning document structure...")
        elements = partition_document(document_path)
        type_counts: dict[str, int] = {}
        for el in elements:
            el_type = el.get("type", "Unknown")
            type_counts[el_type] = type_counts.get(el_type, 0) + 1
        result = json.dumps(
            {
                "total_elements": len(elements),
                "element_types": type_counts,
            },
            indent=2,
        )
        print(f">>> Found {len(elements)} elements across {len(type_counts)} types")
        print(">>> [TOOL DONE]\n")
        return result

    group_chat = GroupChat(
        agents=[user_proxy, document_agent, analyst],
        messages=[],
        max_round=12,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    user_proxy.run(
        manager,
        message=(
            f"Process the document at '{file_path}' using the process_document tool, "
            f"then have the analyst provide a comprehensive analysis of its content."
        ),
    ).process()


# ---------------------------------------------------------------------------
# 4. CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AG2 Multi-Agent Document Processing with Unstructured"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to document file. If not provided, uses a sample from example-docs/.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AG2 + Unstructured: Multi-Agent Document Processing")
    print("=" * 60)
    print()

    main(file_path=args.file)
