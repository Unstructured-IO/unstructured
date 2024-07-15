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

EXPECTED_TEXT_SEMICOLON_DELIMITER = (
    "Year Month Revenue Costs 2022 1 123 -123 2023 2 143,1 -814,38 2024 3 215,32 -11,08"
)

EXPECTED_TABLE_SEMICOLON_DELIMITER = """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>Year</td>
      <td>Month</td>
      <td>Revenue</td>
      <td>Costs</td>
      <td></td>
    </tr>
    <tr>
      <td>2022</td>
      <td>1</td>
      <td>123</td>
      <td>-123</td>
      <td></td>
    </tr>
    <tr>
      <td>2023</td>
      <td>2</td>
      <td>143,1</td>
      <td>-814,38</td>
      <td></td>
    </tr>
    <tr>
      <td>2024</td>
      <td>3</td>
      <td>215,32</td>
      <td>-11,08</td>
      <td></td>
    </tr>
  </tbody>
</table>"""

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

EXPECTED_XLS_TABLE = (
    """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>MC</td>
      <td>What is 2+2?</td>
      <td>4</td>
      <td>correct</td>
      <td>3</td>
      <td>incorrect</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>MA</td>
      <td>What C datatypes are 8 bits? (assume i386)</td>
      <td>int</td>
      <td></td>
      <td>float</td>
      <td></td>
      <td>double</td>
      <td></td>
      <td>char</td>
    </tr>
    <tr>
      <td>TF</td>
      <td>Bagpipes are awesome.</td>
      <td>true</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>ESS</td>
      <td>How have the original Henry Hornbostel buildings """
    """influenced campus architecture and design in the last 30 years?</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>ORD</td>
      <td>Rank the following in their order of operation.</td>
      <td>Parentheses</td>
      <td>Exponents</td>
      <td>Division</td>
      <td>Addition</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>FIB</td>
      <td>The student activities fee is</td>
      <td>95</td>
      <td>dollars for students enrolled in</td>
      <td>19</td>
      <td>units or more,</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>MAT</td>
      <td>Match the lower-case greek letter with its capital form.</td>
      <td>λ</td>
      <td>Λ</td>
      <td>α</td>
      <td>γ</td>
      <td>Γ</td>
      <td>φ</td>
      <td>Φ</td>
    </tr>
  </tbody>
</table>"""
)
