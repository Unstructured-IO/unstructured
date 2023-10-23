EXPECTED_TABLE = """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>Stanley Cups</td>
      <td></td>
      <td></td>
    </tr>
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

EXPECTED_TABLE_XLSX = """<table border="1" class="dataframe">
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

EXPECTED_TITLE = "Stanley Cups"

EXPECTED_TEXT = (
    "Stanley Cups Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
)

EXPECTED_TEXT_XLSX = "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"

EXPECTED_TEXT_WITH_EMOJI = (
    "Stanley Cups "
    "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13 👨\\U+1F3FB🔧 TOR 15"
)

EXPECTED_TABLE_WITH_EMOJI = """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>Stanley Cups</td>
      <td></td>
      <td></td>
    </tr>
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
    <tr>
      <td>👨\\U+1F3FB🔧</td>
      <td>TOR</td>
      <td>15</td>
    </tr>
  </tbody>
</table>"""
