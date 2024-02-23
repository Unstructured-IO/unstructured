from unstructured.partition.pdf import partition_pdf


def test_acciona():
    elements = partition_pdf(
        filename="./example-docs/acciona.pdf",
        strategy="hi_res",
        infer_table_structure=True,
    )
    assert elements is not None

    tables = [el for el in elements if el.category == "Table"]
    assert len(tables) == 1

    table = tables[0]
    assert (
        table.text
        == "Tax jurisdiction Total sales (M€) EBT (M€) Corporate Income Tax accrued (M€) Spain 2,673 367 51 Germany 12 75 -8 Mexico 238 54 19 Australia 881 33 13 Poland 335 19 Australia 4 Saudi Arabia 329 10 6 Portugal 152 9 7 Brazil 44 -8 -16 USA 71 -41 -6 Canada 327 -44 -0.1 Others 1,409 35 27 Total 6,472 508 97 Corporate Income Tax paid on a cash basis (M€) Employees at the close of 2020 Grants (M€) Footnote explaining effective rate due Footnote explaining effective rate paid -0.7 20,860 4.8 1 2 -0.1 428 0 1 2 7.1 1,978 0 5.8 9 0.0 1,704 0 4.5 10 1.4 1,523 0 4 9 6.6 131 0 4 4 5.2 2,015 0.01 7 11 0.2 390 0 3 2 0.0 184 1.3 7 2.10 0.1 1,379 0 7 2 24.8 7,763 0.3 44.5 38,355 6.4 3. Application of unrecorded tax credits. 4. Allocation of consolidation vs local accounts (Corporation Tax payments). 5. Tax rate for Corporation Tax higher than in Spain. 6. Tax rate for Corporation Tax lower than in Spain. 7. Non-capitalisation (recording) of tax credits. 8. Non-deductible expenses and adjustment for inflation. 9. Application of tax credits. 10. Deferral for accelerated depreciation / unrestricted depreciation. 11. Non-application of the tax consolidation system."  # noqa: E501
    )
    assert (
        table.metadata.text_as_html
        == """<table><tr><td>Tax jurisdiction</td><td>Total sales (M€)</td><td>EBT (M€)</td><td>Corporate Income  Tax accrued (M€)</td><td></td><td>Corporate Income Tax  paid on a cash basis (M€)</td><td>Employees at the  close of 2020</td><td>Grants (M€)</td><td>Footnote explaining  effective rate due</td><td>Footnote explaining  effective rate paid</td></tr><tr><td>Spain</td><td>2,673</td><td>367</td><td>51</td><td>-0.7</td><td></td><td>20,860</td><td>4.8</td><td>1</td><td>2</td></tr><tr><td>Germany</td><td>12</td><td>75</td><td>-8</td><td>-0.1</td><td></td><td>428</td><td>0</td><td>1</td><td>2</td></tr><tr><td>Mexico</td><td>238</td><td>54</td><td>19</td><td>7.1</td><td></td><td>1,978</td><td>0</td><td>5.8</td><td>9</td></tr><tr><td>Australia</td><td>881</td><td>33</td><td>13</td><td>0.0</td><td></td><td>1,704</td><td>0</td><td>4.5</td><td>10</td></tr><tr><td>Poland</td><td>335</td><td>19</td><td>4</td><td>1.4</td><td></td><td>1,523</td><td>0</td><td>4</td><td>9</td></tr><tr><td></td><td></td><td>Australia</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>Saudi Arabia</td><td>329</td><td>10</td><td>6</td><td>6.6</td><td></td><td>131</td><td>0</td><td>4</td><td>4</td></tr><tr><td>Portugal</td><td>152</td><td>9</td><td>7</td><td>5.2</td><td></td><td>2,015</td><td>0.01</td><td>7</td><td>11</td></tr><tr><td>Brazil</td><td>44</td><td>-8</td><td>-16</td><td>0.2</td><td></td><td>390</td><td colspan="3" rowspan="2">0  3  2  1.3  7  2.10</td></tr><tr><td>USA</td><td>71</td><td>-41</td><td>-6</td><td>0.0</td><td></td><td>184</td><td colspan="3"></td></tr><tr><td>Others</td><td>1,409</td><td>35</td><td>27</td><td>24.8</td><td></td><td colspan="4">7,763  0.3</td></tr><tr><td>Total</td><td>6,472</td><td>508</td><td>97</td><td colspan="6">44.5</td><td colspan="4">38,355  6.4  8.  Non-deductible expenses and adjustment for inflation. 9.  Application of tax credits. 10. Deferral for accelerated depreciation / unrestricted depreciation. 11.  Non-application of the tax consolidation system.</td></tr></table>"""  # noqa: E501
    )
