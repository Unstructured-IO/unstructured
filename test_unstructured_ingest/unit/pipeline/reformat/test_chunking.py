from __future__ import annotations

import json
import logging
import os

import pytest
from _pytest.logging import LogCaptureFixture

from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    example_doc_path,
    function_mock,
    method_mock,
)
from unstructured.documents.elements import CompositeElement
from unstructured.ingest.interfaces import ChunkingConfig, PartitionConfig
from unstructured.ingest.pipeline.interfaces import PipelineContext
from unstructured.ingest.pipeline.reformat.chunking import Chunker

ELEMENTS_JSON_FILE = example_doc_path(
    "test_evaluate_files/unstructured_output/Bank Good Credit Loan.pptx.json"
)


class DescribeChunker:
    """Unit tests for ingest.pipeline.reformat.chunking.Chunker"""

    # -- Chunker.run() -----------------------------------------------------------------------------

    # -- integration test --
    def it_creates_JSON_elements(self, _ingest_docs_map_: Mock, tmpdir: str):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy="by_title"),
            pipeline_context=PipelineContext(work_dir=tmpdir),
            partition_config=PartitionConfig(),
        )
        # -- `Chunker.chunk()` defaults to writing to "{work_dir}/chunked", which is located in
        # -- "/.cache" of a user's profile.
        # -- Define `work_dir` add the "/chunked" subdirectory to it:
        os.makedirs(os.path.join(tmpdir, "chunked"), exist_ok=True)

        filename = chunker.run(ELEMENTS_JSON_FILE) or ""

        head, tail = os.path.split(filename if filename else "")
        # -- Check that a json file was created in `/chunked` --
        assert head.endswith("chunked")
        assert tail.endswith(".json")
        # -- Check contents of file --
        with open(filename) as json_f:
            json_data = json.load(json_f)
        assert all(d.get("type") == "CompositeElement" for d in json_data)
        assert len(json_data) == 5

    def it_returns_None_and_logs_message_without_chunking_strategy(
        self, _ingest_docs_map_: Mock, caplog: LogCaptureFixture
    ):
        chunker = Chunker(
            chunking_config=ChunkingConfig(),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(),
        )
        caplog.set_level(logging.INFO)

        assert chunker.run(ELEMENTS_JSON_FILE) is None
        assert "chunking_strategy is None, skipping chunking for" in caplog.text

    def it_logs_error_on_invalid_remote_chunking_strategy(
        self, _ingest_docs_map_: Mock, caplog: LogCaptureFixture
    ):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy="by_invalid"),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(partition_by_api=True),
        )

        chunker.run(ELEMENTS_JSON_FILE)

        assert "Input should be 'basic', 'by_page', 'by_similarity'" in caplog.text

    def it_warns_with_nonlocal_chunking_strategy_and_partition_by_api_False(
        self, _ingest_docs_map_: Mock, caplog: LogCaptureFixture
    ):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy="by_similarity"),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(partition_by_api=False),
        )

        chunker.run(ELEMENTS_JSON_FILE)

        assert "There is no locally available chunking_strategy:" in caplog.text

    # -- Chunker.chunk() ---------------------------------------------------------------------------

    def it_skips_chunking_if_strategy_is_None(self):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy=None),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(),
        )

        assert chunker.chunk(ELEMENTS_JSON_FILE) is None

    # -- integration test --
    @pytest.mark.parametrize("strategy", ["by_title", "basic"])
    def it_chunks_locally(self, strategy: str, _ingest_docs_map_: Mock):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy=strategy),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(),
        )

        chunked_elements = chunker.chunk(ELEMENTS_JSON_FILE)

        assert all(isinstance(elem, CompositeElement) for elem in chunked_elements)  # type: ignore

    def it_chunks_remotely(self, _ingest_docs_map_: Mock, _partition_via_api_: Mock):
        chunker = Chunker(
            chunking_config=ChunkingConfig(chunking_strategy="by_similarity"),
            pipeline_context=PipelineContext(),
            partition_config=PartitionConfig(
                partition_by_api=True, api_key="aaaaaaaaaaaaaaaaaaaaa"
            ),
        )

        chunker.chunk(ELEMENTS_JSON_FILE)

        _partition_via_api_.assert_called_once_with(
            filename=ELEMENTS_JSON_FILE,
            api_key="aaaaaaaaaaaaaaaaaaaaa",
            api_url="https://api.unstructured.io/general/v0/general",
            chunking_strategy="by_similarity",
            # (jennings) the sdk uses combine_under_n_chars but the ChunkingConfig param is
            # combine_text_under_n_chars
            combine_under_n_chars=None,
            include_orig_elements=None,
            max_characters=None,
            multipage_sections=None,
            new_after_n_chars=None,
            overlap=None,
            overlap_all=None,
        )

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def _ingest_docs_map_(self, request: FixtureRequest):
        return method_mock(request, PipelineContext, "ingest_docs_map")

    @pytest.fixture()
    def _partition_via_api_(self, request: FixtureRequest):
        return function_mock(
            request, "unstructured.ingest.pipeline.reformat.chunking.partition_via_api"
        )
