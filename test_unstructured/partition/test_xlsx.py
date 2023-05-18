from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.xlsx import partition_xlsx

EXPECTED_TABLE = """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>Team</td>
      <td>Location</td>
      <td>Stanley Cups</td>
    </tr>
    <tr>
      <td>Blues</td>
      <td>STL</td>
      <td>1</td>
    </tr>
    <tr>
      <td>Flyers</td>
      <td>PHI</td>
      <td>2</td>
    </tr>
    <tr>
      <td>Maple Leafs</td>
      <td>TOR</td>
      <td>13</td>
    </tr>
  </tbody>
</table>"""


EXPECTED_TEXT = "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"

EXPECTED_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXCEPTED_PAGE_NAME = "Stanley Cups"


def test_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.page_name == EXCEPTED_PAGE_NAME


def test_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.page_name == EXCEPTED_PAGE_NAME


def test_partition_xlsx_can_exclude_metadata(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_metadata=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.page_number is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
