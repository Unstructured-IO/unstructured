"""Test suite for the `unstructured.chunking.basic` module.

That module implements the baseline chunking strategy. The baseline strategy has all behaviors
shared by all chunking strategies and no extra rules like perserve section or page boundaries.
"""

from __future__ import annotations

from typing import Any

import pytest

from test_unstructured.unit_utils import FixtureRequest, Mock, function_mock
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import (
    CompositeElement,
    ElementMetadata,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.docx import partition_docx


def test_it_chunks_a_document_when_basic_chunking_strategy_is_specified_on_partition_function():
    """Basic chunking can be combined with partitioning, exercising the decorator."""
    filename = "example-docs/handbook-1p.docx"

    chunks = partition_docx(filename, chunking_strategy="basic")

    assert chunks == [
        CompositeElement(
            "US Trustee Handbook\n\nCHAPTER 1\n\nINTRODUCTION\n\nCHAPTER 1 – INTRODUCTION"
            "\n\nA. PURPOSE"
        ),
        CompositeElement(
            "The United States Trustee appoints and supervises standing trustees and monitors and"
            " supervises cases under chapter 13 of title 11 of the United States Code. 28 U.S.C."
            " § 586(b). The Handbook, issued as part of our duties under 28 U.S.C. § 586,"
            " establishes or clarifies the position of the United States Trustee Program (Program)"
            " on the duties owed by a standing trustee to the debtors, creditors, other parties in"
            " interest, and the United States Trustee. The Handbook does not present a full and"
        ),
        CompositeElement(
            "complete statement of the law; it should not be used as a substitute for legal"
            " research and analysis. The standing trustee must be familiar with relevant"
            " provisions of the Bankruptcy Code, Federal Rules of Bankruptcy Procedure (Rules),"
            " any local bankruptcy rules, and case law. 11 U.S.C. § 321, 28 U.S.C. § 586,"
            " 28 C.F.R. § 58.6(a)(3). Standing trustees are encouraged to follow Practice Tips"
            " identified in this Handbook but these are not considered mandatory."
        ),
        CompositeElement(
            "Nothing in this Handbook should be construed to excuse the standing trustee from"
            " complying with all duties imposed by the Bankruptcy Code and Rules, local rules, and"
            " orders of the court. The standing trustee should notify the United States Trustee"
            " whenever the provision of the Handbook conflicts with the local rules or orders of"
            " the court. The standing trustee is accountable for all duties set forth in this"
            " Handbook, but need not personally perform any duty unless otherwise indicated. All"
        ),
        CompositeElement(
            "statutory references in this Handbook refer to the Bankruptcy Code, 11 U.S.C. § 101"
            " et seq., unless otherwise indicated."
        ),
        CompositeElement(
            "This Handbook does not create additional rights against the standing trustee or"
            " United States Trustee in favor of other parties.\n\nB. ROLE OF THE UNITED STATES"
            " TRUSTEE"
        ),
        CompositeElement(
            "The Bankruptcy Reform Act of 1978 removed the bankruptcy judge from the"
            " responsibilities for daytoday administration of cases. Debtors, creditors, and"
            " third parties with adverse interests to the trustee were concerned that the court,"
            " which previously appointed and supervised the trustee, would not impartially"
            " adjudicate their rights as adversaries of that trustee. To address these concerns,"
            " judicial and administrative functions within the bankruptcy system were bifurcated."
        ),
        CompositeElement(
            "Many administrative functions formerly performed by the court were placed within the"
            " Department of Justice through the creation of the Program. Among the administrative"
            " functions assigned to the United States Trustee were the appointment and supervision"
            " of chapter 13 trustees./ This Handbook is issued under the authority of the"
            " Program’s enabling statutes.\n\nC. STATUTORY DUTIES OF A STANDING TRUSTEE"
        ),
        CompositeElement(
            "The standing trustee has a fiduciary responsibility to the bankruptcy estate. The"
            " standing trustee is more than a mere disbursing agent. The standing trustee must"
            " be personally involved in the trustee operation. If the standing trustee is or"
            " becomes unable to perform the duties and responsibilities of a standing trustee,"
            " the standing trustee must immediately advise the United States Trustee."
            " 28 U.S.C. § 586(b), 28 C.F.R. § 58.4(b) referencing 28 C.F.R. § 58.3(b)."
        ),
        CompositeElement(
            "Although this Handbook is not intended to be a complete statutory reference, the"
            " standing trustee’s primary statutory duties are set forth in 11 U.S.C. § 1302, which"
            " incorporates by reference some of the duties of chapter 7 trustees found in"
            " 11 U.S.C. § 704. These duties include, but are not limited to, the"
            " following:\n\nCopyright"
        ),
    ]


def test_it_chunks_elements_when_the_user_already_has_them():
    elements = [
        Title("Introduction"),
        Text(
            # --------------------------------------------------------- 64 -v
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed lectus"
            " porta volutpat.",
        ),
    ]

    chunks = chunk_elements(elements, max_characters=64)

    assert chunks == [
        CompositeElement("Introduction"),
        # -- splits on even word boundary, not mid-"rhoncus" --
        CompositeElement("Lorem ipsum dolor sit amet consectetur adipiscing elit. In"),
        CompositeElement("rhoncus ipsum sed lectus porta volutpat."),
    ]


def test_it_includes_original_elements_as_metadata_when_requested():
    element = Title("Introduction")
    element_2 = Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")
    element_3 = Text("In rhoncus ipsum sed lectus porta volutpat.")

    chunks = chunk_elements(
        [element, element_2, element_3], max_characters=70, include_orig_elements=True
    )

    assert len(chunks) == 2
    chunk = chunks[0]
    assert chunk == CompositeElement(
        "Introduction\n\nLorem ipsum dolor sit amet consectetur adipiscing elit."
    )
    assert chunk.metadata.orig_elements == [element, element_2]
    # --
    chunk = chunks[1]
    assert chunk == CompositeElement("In rhoncus ipsum sed lectus porta volutpat.")
    assert chunk.metadata.orig_elements == [element_3]


def test_it_repeats_table_headers_by_default_but_can_opt_out():
    table_html = (
        "<table>"
        "<thead>"
        "<tr><th>Header A</th><th>Header B</th></tr>"
        "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
        "</thead>"
        "<tbody>"
        "<tr><td>Body 1</td><td>Alpha</td></tr>"
        "<tr><td>Body 2</td><td>Bravo</td></tr>"
        "<tr><td>Body 3</td><td>Charlie</td></tr>"
        "<tr><td>Body 4</td><td>Delta</td></tr>"
        "</tbody>"
        "</table>"
    )
    table_text = (
        "Header A Header B\n"
        "Subhead A Subhead B\n"
        "Body 1 Alpha\n"
        "Body 2 Bravo\n"
        "Body 3 Charlie\n"
        "Body 4 Delta"
    )
    table = Table(table_text, metadata=ElementMetadata(text_as_html=table_html))

    repeated_header_chunks = chunk_elements([table], max_characters=55)
    opt_out_chunks = chunk_elements([table], max_characters=55, repeat_table_headers=False)

    assert len(repeated_header_chunks) == 4
    assert all(isinstance(chunk, TableChunk) for chunk in repeated_header_chunks)
    assert [chunk.text for chunk in repeated_header_chunks] == [
        "Header A Header B Subhead A Subhead B Body 1 Alpha",
        "Header A Header B Subhead A Subhead B Body 2 Bravo",
        "Header A Header B Subhead A Subhead B Body 3 Charlie",
        "Header A Header B Subhead A Subhead B Body 4 Delta",
    ]
    assert [chunk.text for chunk in opt_out_chunks] == [
        "Header A Header B Subhead A Subhead B Body 1 Alpha",
        "Body 2 Bravo Body 3 Charlie Body 4 Delta",
    ]


# ------------------------------------------------------------------------------------------------
# UNIT TESTS
# ------------------------------------------------------------------------------------------------


class Describe_chunk_elements:
    """Unit-test suite for `unstructured.chunking.basic.chunk_elements()` function."""

    @pytest.mark.parametrize(
        ("kwargs", "expected_value"),
        [
            ({"include_orig_elements": True}, True),
            ({"include_orig_elements": False}, False),
            ({"include_orig_elements": None}, True),
            ({}, True),
        ],
    )
    def it_supports_the_include_orig_elements_option(
        self, kwargs: dict[str, Any], expected_value: bool, _chunk_elements_: Mock
    ):
        # -- this line would raise if "include_orig_elements" was not an available parameter on
        # -- `chunk_elements()`.
        chunk_elements([], **kwargs)

        _, opts = _chunk_elements_.call_args.args
        assert opts.include_orig_elements is expected_value

    @pytest.mark.parametrize(
        ("kwargs", "expected_value"),
        [
            ({"repeat_table_headers": True}, True),
            ({"repeat_table_headers": False}, False),
            ({"repeat_table_headers": None}, True),
            ({}, True),
        ],
    )
    def it_supports_the_repeat_table_headers_option(
        self, kwargs: dict[str, Any], expected_value: bool, _chunk_elements_: Mock
    ):
        # -- this line would raise if "repeat_table_headers" was not an available parameter on
        # -- `chunk_elements()`.
        chunk_elements([], **kwargs)

        _, opts = _chunk_elements_.call_args.args
        assert opts.repeat_table_headers is expected_value

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def _chunk_elements_(self, request: FixtureRequest):
        return function_mock(request, "unstructured.chunking.basic._chunk_elements")
