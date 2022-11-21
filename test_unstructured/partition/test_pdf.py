import unstructured.partition.pdf as pdf


def test_partition_pdf(filename="example-docs/layout-parser-paper-fast.pdf"):
    partition_pdf_response = pdf.partition_pdf(filename)
    assert partition_pdf_response[0]["type"] == "Title"
    assert (
        partition_pdf_response[0]["text"]
        == "LayoutParser : A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    )
