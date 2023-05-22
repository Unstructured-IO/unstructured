from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.csv import partition_csv

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

EXPECTED_FILETYPE = "text/csv"


def test_partition_csv_from_filename(filename="example-docs/stanley-cups.csv"):
    elements = partition_csv(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE


def test_partition_csv_from_file(filename="example-docs/stanley-cups.csv"):
    with open(filename, "rb") as f:
        elements = partition_csv(file=f)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE


def test_partition_csv_can_exclude_metadata(filename="example-docs/stanley-cups.csv"):
    elements = partition_csv(filename=filename, include_metadata=False)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.filetype is None
