"""Test suite for the `unstructured.chunking.basic` module.

That module implements the baseline chunking strategy. The baseline strategy has all behaviors
shared by all chunking strategies and no extra rules like perserve section or page boundaries.
"""

from __future__ import annotations

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import CompositeElement, Text, Title
from unstructured.partition.docx import partition_docx


def test_it_chunks_a_document_when_basic_chunking_strategy_is_specified_on_partition_function():
    """Basic chunking can be combined with partitioning, exercising the decorator."""
    filename = "example-docs/handbook-1p.docx"

    chunks = partition_docx(filename, chunking_strategy="basic")

    assert chunks == [
        CompositeElement(
            "US Trustee Handbook\n\nCHAPTER 1\n\nINTRODUCTION\n\nCHAPTER 1 – INTRODUCTION"
            "\n\nA.\tPURPOSE"
        ),
        CompositeElement(
            "The United States Trustee appoints and supervises standing trustees and monitors and"
            " supervises cases under chapter 13 of title 11 of the United States Code.  28 U.S.C."
            " § 586(b).  The Handbook, issued as part of our duties under 28 U.S.C. § 586,"
            " establishes or clarifies the position of the United States Trustee Program (Program)"
            " on the duties owed by a standing trustee to the debtors, creditors, other parties in"
            " interest, and the United States Trustee.  The Handbook does not present a full and"
        ),
        CompositeElement(
            "complete statement of the law; it should not be used as a substitute for legal"
            " research and analysis.  The standing trustee must be familiar with relevant"
            " provisions of the Bankruptcy Code, Federal Rules of Bankruptcy Procedure (Rules),"
            " any local bankruptcy rules, and case law.  11 U.S.C. § 321, 28 U.S.C. § 586,"
            " 28 C.F.R. § 58.6(a)(3).  Standing trustees are encouraged to follow Practice Tips"
            " identified in this Handbook but these are not considered mandatory."
        ),
        CompositeElement(
            "Nothing in this Handbook should be construed to excuse the standing trustee from"
            " complying with all duties imposed by the Bankruptcy Code and Rules, local rules, and"
            " orders of the court.  The standing trustee should notify the United States Trustee"
            " whenever the provision of the Handbook conflicts with the local rules or orders of"
            " the court.  The standing trustee is accountable for all duties set forth in this"
            " Handbook, but need not personally perform any duty unless otherwise indicated.  All"
        ),
        CompositeElement(
            "statutory references in this Handbook refer to the Bankruptcy Code, 11 U.S.C. § 101"
            " et seq., unless otherwise indicated."
        ),
        CompositeElement(
            "This Handbook does not create additional rights against the standing trustee or"
            " United States Trustee in favor of other parties.\n\nB.\tROLE OF THE UNITED STATES"
            " TRUSTEE"
        ),
        CompositeElement(
            "The Bankruptcy Reform Act of 1978 removed the bankruptcy judge from the"
            " responsibilities for daytoday administration of cases.  Debtors, creditors, and"
            " third parties with adverse interests to the trustee were concerned that the court,"
            " which previously appointed and supervised the trustee, would not impartially"
            " adjudicate their rights as adversaries of that trustee. To address these concerns,"
            " judicial and administrative functions within the bankruptcy system were bifurcated."
        ),
        CompositeElement(
            "Many administrative functions formerly performed by the court were placed within the"
            " Department of Justice through the creation of the Program.  Among the administrative"
            " functions assigned to the United States Trustee were the appointment and supervision"
            " of chapter 13 trustees./  This Handbook is issued under the authority of the"
            " Program’s enabling statutes. \n\nC.\tSTATUTORY DUTIES OF A STANDING TRUSTEE\t"
        ),
        CompositeElement(
            "The standing trustee has a fiduciary responsibility to the bankruptcy estate.  The"
            " standing trustee is more than a mere disbursing agent.  The standing trustee must"
            " be personally involved in the trustee operation.  If the standing trustee is or"
            " becomes unable to perform the duties and responsibilities of a standing trustee,"
            " the standing trustee must immediately advise the United States Trustee."
            "  28 U.S.C. § 586(b), 28 C.F.R. § 58.4(b) referencing 28 C.F.R. § 58.3(b)."
        ),
        CompositeElement(
            "Although this Handbook is not intended to be a complete statutory reference, the"
            " standing trustee’s primary statutory duties are set forth in 11 U.S.C. § 1302, which"
            " incorporates by reference some of the duties of chapter 7 trustees found in"
            " 11 U.S.C. § 704.  These duties include, but are not limited to, the"
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
