"""End-to-end tests for AG2 + Unstructured document processing example.

Run these tests to verify the integration works correctly before submitting a PR.

Usage:
    # Run all e2e tests (no API key needed for most tests):
    pytest examples/ag2_multiagent_document_processing/test_e2e.py -v

    # Run only offline tests (no API key needed):
    pytest examples/ag2_multiagent_document_processing/test_e2e.py -v -k "not live_llm"

    # Run full pipeline test with live LLM (requires OPENAI_API_KEY):
    pytest examples/ag2_multiagent_document_processing/test_e2e.py -v -k "live_llm"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
EXAMPLE_DOCS = REPO_ROOT / "example-docs"

from examples.ag2_multiagent_document_processing.run import (  # noqa: E402
    filter_elements_by_confidence,
    find_sample_document,
    format_elements_summary,
    partition_document,
)

# ---------------------------------------------------------------------------
# Test 1: Unstructured can partition documents
# ---------------------------------------------------------------------------


class TestUnstructuredPartitioning:
    """Verify that Unstructured correctly partitions different document types."""

    def test_partition_html(self) -> None:
        """Partition a sample HTML file and verify elements are extracted."""
        html_files = list(EXAMPLE_DOCS.glob("*.html"))
        if not html_files:
            pytest.skip("No HTML files in example-docs/")

        elements = partition_document(str(html_files[0]))

        assert isinstance(elements, list), "partition_document should return a list"
        assert len(elements) > 0, "HTML should produce at least one element"

        first = elements[0]
        assert "type" in first, "Element must have a 'type' field"

    def test_partition_nonexistent_file(self) -> None:
        """Verify graceful handling of missing files."""
        with pytest.raises(Exception):
            partition_document("/nonexistent/file.pdf")

    def test_element_types_present(self) -> None:
        """Verify common element types are detected in a rich document."""
        html_10k = EXAMPLE_DOCS / "example-10k-1p.html"
        if not html_10k.exists():
            pytest.skip("example-10k-1p.html not found")

        elements = partition_document(str(html_10k))
        types = {el.get("type") for el in elements}

        assert "Title" in types or "NarrativeText" in types, (
            f"Expected Title or NarrativeText in rich document, got: {types}"
        )


# ---------------------------------------------------------------------------
# Test 2: Element formatting works correctly
# ---------------------------------------------------------------------------


class TestFormatting:
    """Verify that extracted elements are formatted correctly for AG2 agents."""

    def test_format_elements_summary_basic(self) -> None:
        """Test formatting with sample element dicts."""
        elements = [
            {"type": "Title", "text": "Introduction"},
            {"type": "NarrativeText", "text": "This is the main content of the document."},
            {"type": "ListItem", "text": "First item in the list"},
            {"type": "ListItem", "text": "Second item in the list"},
        ]

        summary = format_elements_summary(elements)

        assert "4 elements" in summary, "Should report total element count"
        assert "Title" in summary, "Should include Title element type"
        assert "NarrativeText" in summary, "Should include NarrativeText"
        assert "ListItem" in summary, "Should include ListItem"
        assert "Introduction" in summary, "Should include actual text content"

    def test_format_elements_summary_empty(self) -> None:
        """Test formatting with empty element list."""
        summary = format_elements_summary([])
        assert "0 elements" in summary

    def test_format_elements_truncation(self) -> None:
        """Test that long text is truncated in formatting."""
        elements = [
            {"type": "NarrativeText", "text": "x" * 1000},
        ]

        summary = format_elements_summary(elements)
        assert "truncated" in summary, "Long text should be marked as truncated"

    def test_format_includes_confidence_scores(self) -> None:
        """Test that confidence scores are shown when present."""
        elements = [
            {
                "type": "Title",
                "text": "High confidence title",
                "metadata": {"detection_class_prob": 0.95},
            },
            {
                "type": "NarrativeText",
                "text": "No confidence text",
                "metadata": {},
            },
        ]

        summary = format_elements_summary(elements)
        assert "[conf=0.95]" in summary, "Should show confidence for scored elements"
        # The NarrativeText line should NOT have a conf= tag
        for line in summary.splitlines():
            if "No confidence text" in line:
                assert "[conf=" not in line, "No score element should not show conf="


# ---------------------------------------------------------------------------
# Test 3: Confidence score filtering
# ---------------------------------------------------------------------------


class TestConfidenceFiltering:
    """Verify confidence-based element filtering (addresses issue #4320)."""

    def test_filter_keeps_high_confidence(self) -> None:
        """Elements above threshold are kept."""
        elements = [
            {"type": "Title", "text": "Good", "metadata": {"detection_class_prob": 0.9}},
            {"type": "NarrativeText", "text": "Bad", "metadata": {"detection_class_prob": 0.2}},
        ]
        result = filter_elements_by_confidence(elements, min_confidence=0.5)
        assert len(result["kept"]) == 1
        assert result["kept"][0]["text"] == "Good"
        assert len(result["filtered_out"]) == 1

    def test_filter_keeps_elements_without_score(self) -> None:
        """Elements without confidence scores are kept by default."""
        elements = [
            {"type": "Title", "text": "No score", "metadata": {}},
            {"type": "NarrativeText", "text": "Also no score"},
        ]
        result = filter_elements_by_confidence(elements, min_confidence=0.5)
        assert len(result["kept"]) == 2
        assert result["stats"]["no_score"] == 2

    def test_filter_stats_are_correct(self) -> None:
        """Verify filter stats report correct counts."""
        elements = [
            {"type": "Title", "text": "A", "metadata": {"detection_class_prob": 0.9}},
            {"type": "Title", "text": "B", "metadata": {"detection_class_prob": 0.3}},
            {"type": "Title", "text": "C", "metadata": {}},
        ]
        result = filter_elements_by_confidence(elements, min_confidence=0.5)
        stats = result["stats"]
        assert stats["total"] == 3
        assert stats["kept"] == 2
        assert stats["filtered_out"] == 1
        assert stats["no_score"] == 1
        assert stats["min_confidence"] == 0.5

    def test_filter_with_zero_threshold(self) -> None:
        """Zero threshold keeps everything with a score."""
        elements = [
            {"type": "Title", "text": "A", "metadata": {"detection_class_prob": 0.01}},
            {"type": "Title", "text": "B", "metadata": {"detection_class_prob": 0.0}},
        ]
        result = filter_elements_by_confidence(elements, min_confidence=0.0)
        assert len(result["kept"]) == 2
        assert len(result["filtered_out"]) == 0


# ---------------------------------------------------------------------------
# Test 4: Sample document finder works
# ---------------------------------------------------------------------------


class TestSampleDocumentFinder:
    """Verify the sample document finder locates files correctly."""

    def test_find_sample_document(self) -> None:
        """Find a sample document from example-docs/."""
        if not EXAMPLE_DOCS.exists():
            pytest.skip("example-docs/ not found -- run from repo root")

        doc_path = find_sample_document()
        assert os.path.exists(doc_path), f"Sample document should exist: {doc_path}"
        assert os.path.getsize(doc_path) > 0, "Sample document should not be empty"


# ---------------------------------------------------------------------------
# Test 5: AG2 agent setup works (no LLM call)
# ---------------------------------------------------------------------------


class TestAG2AgentSetup:
    """Verify AG2 agents and tools are configured correctly (no API calls)."""

    def test_ag2_imports(self) -> None:
        """Verify AG2 imports work correctly."""
        from autogen import (
            AssistantAgent,
            GroupChat,
            GroupChatManager,
            LLMConfig,
            UserProxyAgent,
        )

        assert AssistantAgent is not None
        assert UserProxyAgent is not None
        assert GroupChat is not None
        assert GroupChatManager is not None
        assert LLMConfig is not None

    def test_llm_config_creation(self) -> None:
        """Verify LLMConfig accepts the positional dict pattern."""
        from autogen import LLMConfig

        config = LLMConfig(
            {
                "model": "gpt-4o-mini",
                "api_key": "test-key-not-real",
                "api_type": "openai",
            }
        )
        assert config is not None

    def test_agent_creation(self) -> None:
        """Verify agents can be created with the correct pattern."""
        from autogen import AssistantAgent, LLMConfig, UserProxyAgent

        llm_config = LLMConfig(
            {
                "model": "gpt-4o-mini",
                "api_key": "test-key-not-real",
                "api_type": "openai",
            }
        )

        agent = AssistantAgent(
            name="test_agent",
            system_message="Test agent",
            llm_config=llm_config,
        )
        assert agent.name == "test_agent"

        proxy = UserProxyAgent(
            name="test_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False,
        )
        assert proxy.name == "test_proxy"

    def test_tool_registration(self) -> None:
        """Verify tool registration via decorator pattern works."""
        from autogen import AssistantAgent, LLMConfig, UserProxyAgent

        llm_config = LLMConfig(
            {
                "model": "gpt-4o-mini",
                "api_key": "test-key-not-real",
                "api_type": "openai",
            }
        )

        assistant = AssistantAgent(
            name="assistant",
            system_message="Test",
            llm_config=llm_config,
        )
        proxy = UserProxyAgent(
            name="proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
        )

        @proxy.register_for_execution()
        @assistant.register_for_llm(description="Test tool")
        def test_tool(query: str) -> str:
            return f"Result for: {query}"

        assert test_tool("hello") == "Result for: hello"


# ---------------------------------------------------------------------------
# Test 6: Full pipeline with LIVE LLM (requires API key)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set -- skipping live LLM test",
)
class TestLiveLLMPipeline:
    """Full end-to-end test with actual LLM calls. Requires OPENAI_API_KEY."""

    def test_live_llm_full_pipeline(self) -> None:
        """Run the complete AG2 + Unstructured pipeline with a real LLM."""
        from autogen import (
            AssistantAgent,
            GroupChat,
            GroupChatManager,
            LLMConfig,
            UserProxyAgent,
        )

        test_doc = EXAMPLE_DOCS / "example-10k-1p.html"
        if not test_doc.exists():
            html_files = list(EXAMPLE_DOCS.glob("*.html"))
            if not html_files:
                pytest.skip("No HTML test documents available")
            test_doc = html_files[0]

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
                "You are a document processing agent. Use the process_document "
                "tool to extract content from the specified document."
            ),
            llm_config=llm_config,
        )

        analyst = AssistantAgent(
            name="analyst",
            system_message=("Summarize the document content in 2-3 sentences. End with TERMINATE."),
            llm_config=llm_config,
        )

        user_proxy = UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=5,
            code_execution_config=False,
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        )

        @user_proxy.register_for_execution()
        @document_agent.register_for_llm(
            description="Process a document and extract structured content."
        )
        def process_document(document_path: str) -> str:
            elements = partition_document(document_path)
            return format_elements_summary(elements[:20])

        group_chat = GroupChat(
            agents=[user_proxy, document_agent, analyst],
            messages=[],
            max_round=8,
        )

        manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

        user_proxy.run(
            manager,
            message=f"Process the document at '{test_doc}' and summarize it.",
        ).process()

        all_messages = group_chat.messages
        assert len(all_messages) > 2, (
            f"Expected multi-turn conversation, got {len(all_messages)} messages"
        )

        last_messages = [m.get("content", "") for m in all_messages[-3:]]
        assert any("TERMINATE" in msg for msg in last_messages), (
            "Analyst should have terminated the conversation"
        )
