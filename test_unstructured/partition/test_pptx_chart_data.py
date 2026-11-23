from io import BytesIO

import pytest
from lxml import etree
from pptx import Presentation
from pptx.chart.category import Categories
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.oxml.ns import qn
from pptx.util import Inches

from unstructured.documents.elements import Table, Title
from unstructured.partition.pptx import partition_pptx


def chart_deck(chart_type=XL_CHART_TYPE.COLUMN_CLUSTERED, *, hierarchical=False, slide_title=None):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5 if slide_title else 6])
    if slide_title:
        slide.shapes.title.text = slide_title
    data = CategoryChartData()
    if hierarchical:
        north = data.add_category("North")
        north.add_sub_category("Online")
        north.add_sub_category("Retail")
        south = data.add_category("South")
        south.add_sub_category("Online")
    else:
        data.categories = ["East & West", "<Central>", "South"]
    data.add_series("Sales <USD>", [0, 2.5, None])
    if chart_type not in (XL_CHART_TYPE.PIE, XL_CHART_TYPE.DOUGHNUT):
        data.add_series("Profit", [-1, None, 4])
    shape = slide.shapes.add_chart(chart_type, Inches(1), Inches(1), Inches(5), Inches(4), data)
    shape.chart.has_title = True
    shape.chart.chart_title.text_frame.text = "Quarterly results"
    return presentation, shape


def save(presentation):
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()


def table_cells(table):
    return [
        ["".join(cell.itertext()) for cell in row]
        for row in etree.fromstring(table.metadata.text_as_html.encode()).xpath(".//tr")
    ]


@pytest.mark.parametrize(
    "chart_type",
    [
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        XL_CHART_TYPE.LINE,
        XL_CHART_TYPE.AREA,
        XL_CHART_TYPE.PIE,
        XL_CHART_TYPE.DOUGHNUT,
        XL_CHART_TYPE.RADAR,
    ],
)
@pytest.mark.parametrize("infer_table_structure", [False, True])
def test_category_chart_titles_and_cached_values_are_retained(chart_type, infer_table_structure):
    presentation, _ = chart_deck(chart_type)
    payload = save(presentation)
    source = BytesIO(payload)

    elements = partition_pptx(
        file=source,
        infer_table_structure=infer_table_structure,
        starting_page_number=7,
        languages=["eng"],
    )

    assert [type(element) for element in elements] == [Title, Table]
    title, table = elements
    assert title.text == "Quarterly results"
    assert all(element.metadata.page_number == 7 for element in elements)
    assert "Sales <USD>" in table.text
    assert "East & West" in table.text
    assert "0.0" in table.text
    assert "2.5" in table.text
    assert "None" not in table.text
    if infer_table_structure:
        expected = [
            ["Category", "Sales <USD>"],
            ["East & West", "0.0"],
            ["<Central>", "2.5"],
            ["South", ""],
        ]
        if chart_type not in (XL_CHART_TYPE.PIE, XL_CHART_TYPE.DOUGHNUT):
            for row, value in zip(expected, ["Profit", "-1.0", "", "4.0"]):
                row.append(value)
        assert table_cells(table) == expected
    else:
        assert table.metadata.text_as_html is None
    assert source.getvalue() == payload


@pytest.mark.parametrize("source", ["file", "filename"])
def test_hierarchical_categories_preserve_each_level_and_alignment(tmp_path, source):
    presentation, _ = chart_deck(hierarchical=True)
    payload = save(presentation)
    path = tmp_path / "hierarchical.pptx"
    path.write_bytes(payload)
    kwargs = {"file": BytesIO(payload)} if source == "file" else {"filename": str(path)}

    _, table = partition_pptx(**kwargs, languages=["eng"])

    assert table_cells(table) == [
        ["Category 1", "Category 2", "Sales <USD>", "Profit"],
        ["North", "Online", "0.0", "-1.0"],
        ["North", "Retail", "2.5", ""],
        ["South", "Online", "", "4.0"],
    ]


def test_multiple_plots_keep_independent_category_series_tables():
    presentation, first = chart_deck()
    _, second = chart_deck(XL_CHART_TYPE.LINE, hierarchical=True)
    line_plot = second.chart._chartSpace.xpath(".//c:lineChart")[0]
    first.chart._chartSpace.xpath(".//c:plotArea")[0].insert(1, line_plot)

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert [type(element) for element in elements] == [Title, Table, Table]
    assert table_cells(elements[1])[1][0] == "East & West"
    assert table_cells(elements[2])[1][:2] == ["North", "Online"]


def test_chart_data_can_be_disabled():
    presentation, _ = chart_deck()

    assert partition_pptx(file=BytesIO(save(presentation)), include_chart_data=False) == []


def test_chart_without_title_is_not_mutated_to_add_one():
    presentation, shape = chart_deck()
    shape.chart.has_title = False
    payload = save(presentation)
    source = BytesIO(payload)

    elements = partition_pptx(file=source, languages=["eng"])

    assert len(elements) == 1
    assert isinstance(elements[0], Table)
    assert not shape.chart.has_title
    assert source.getvalue() == payload


def test_xy_charts_keep_the_title_without_mislabeling_coordinates_as_categories():
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    data = XyChartData()
    data.add_series("Observations").add_data_point(10, 20)
    shape = slide.shapes.add_chart(
        XL_CHART_TYPE.XY_SCATTER, Inches(1), Inches(1), Inches(5), Inches(4), data
    )
    shape.chart.has_title = True
    shape.chart.chart_title.text_frame.text = "Observations by position"

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert [element.text for element in elements] == ["Observations by position"]
    assert isinstance(elements[0], Title)


@pytest.mark.parametrize("include_off_slide_shapes", [False, True])
def test_chart_extraction_obeys_existing_off_slide_shape_option(include_off_slide_shapes):
    presentation, shape = chart_deck()
    shape.left = Inches(30)

    elements = partition_pptx(
        file=BytesIO(save(presentation)),
        include_off_slide_shapes=include_off_slide_shapes,
        languages=["eng"],
    )

    assert len(elements) == (2 if include_off_slide_shapes else 0)


def test_unsupported_plot_does_not_discard_the_chart_title_or_following_text(caplog):
    presentation, shape = chart_deck()
    plot = shape.chart._chartSpace.xpath(".//c:barChart")[0]
    plot.tag = "{http://schemas.openxmlformats.org/drawingml/2006/chart}surfaceChart"
    slide = presentation.slides[0]
    slide.shapes.add_textbox(Inches(1), Inches(5), Inches(5), Inches(1)).text = "Following content"

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert [element.text for element in elements] == ["Quarterly results", "Following content"]
    assert "Skipping unsupported PPTX chart plot" in caplog.text


@pytest.mark.parametrize("cache", ["category", "series", "total_cells", "sparse_index"])
def test_chart_size_is_bounded_before_expanding_cache_values(monkeypatch, cache, caplog):
    presentation, shape = chart_deck()
    space = shape.chart._chartSpace
    if cache == "category":
        space.xpath(".//c:cat//c:ptCount")[0].set("val", "1000000000")
    elif cache == "series":
        space.xpath(".//c:val//c:ptCount")[0].set("val", "1000000000")
    elif cache == "sparse_index":
        space.xpath(".//c:cat//c:pt")[0].set("idx", "1000000000")
    else:
        for count in space.xpath(".//c:cat//c:ptCount | .//c:val//c:ptCount"):
            count.set("val", "40000")
    presentation.slides[0].shapes.add_textbox(
        Inches(1), Inches(6), Inches(5), Inches(1)
    ).text = "Following content"

    def expanded(_):
        pytest.fail("an oversized cache reached dense category expansion")

    monkeypatch.setattr(Categories, "flattened_labels", property(expanded))
    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert [element.text for element in elements] == ["Quarterly results", "Following content"]
    assert "Skipping unsupported PPTX chart plot" in caplog.text


def test_chart_cell_budget_is_shared_by_its_plots(monkeypatch, caplog):
    import unstructured.partition.pptx as pptx_partitioner

    presentation, shape = chart_deck()
    _, second = chart_deck(XL_CHART_TYPE.LINE)
    line_plot = second.chart._chartSpace.xpath(".//c:lineChart")[0]
    shape.chart._chartSpace.xpath(".//c:plotArea")[0].insert(1, line_plot)
    monkeypatch.setattr(pptx_partitioner, "_MAX_CHART_CELLS", 18, raising=False)

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert [type(element) for element in elements] == [Title, Table]
    assert table_cells(elements[1])[1] == ["East & West", "0.0", "-1.0"]
    assert "Skipping unsupported PPTX chart plot" in caplog.text


def test_empty_numeric_points_preserve_positions_and_following_content():
    presentation, shape = chart_deck()
    shape.chart._chartSpace.xpath(".//c:ser[1]/c:val//c:pt[@idx='1']/c:v")[0].text = None
    presentation.slides[0].shapes.add_textbox(
        Inches(1), Inches(6), Inches(5), Inches(1)
    ).text = "Following content"

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert table_cells(elements[1]) == [
        ["Category", "Sales <USD>", "Profit"],
        ["East & West", "0.0", "-1.0"],
        ["<Central>", "", ""],
        ["South", "", "4.0"],
    ]
    assert elements[-1].text == "Following content"


def test_sparse_hierarchical_categories_preserve_leaf_indices():
    presentation, shape = chart_deck(hierarchical=True)
    leaf = shape.chart._chartSpace.xpath(".//c:cat//c:lvl[1]/c:pt[@idx='1']")[0]
    leaf.getparent().remove(leaf)

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert table_cells(elements[1]) == [
        ["Category 1", "Category 2", "Sales <USD>", "Profit"],
        ["North", "Online", "0.0", "-1.0"],
        ["North", "", "2.5", ""],
        ["South", "Online", "", "4.0"],
    ]


def test_chart_title_keeps_the_slide_title_as_ancestor():
    presentation, _ = chart_deck(slide_title="Financials")
    presentation.slides[0].shapes.add_textbox(
        Inches(1), Inches(6), Inches(5), Inches(1)
    ).text = "Next section"

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])
    slide, chart, _, following = elements

    assert slide.text == "Financials"
    assert chart.metadata.category_depth == 1
    assert chart.metadata.parent_id == slide.id
    assert following.metadata.parent_id == slide.id


def test_literal_series_names_remain_distinct():
    presentation, shape = chart_deck()
    for tx, name in zip(shape.chart._chartSpace.xpath(".//c:ser/c:tx"), ["Revenue", "Costs"]):
        for child in list(tx):
            tx.remove(child)
        etree.SubElement(tx, qn("c:v")).text = name

    elements = partition_pptx(file=BytesIO(save(presentation)), languages=["eng"])

    assert table_cells(elements[1])[0] == ["Category", "Revenue", "Costs"]


@pytest.mark.parametrize("scatter", [False, True])
def test_cached_reference_titles_are_retained_without_external_reads(scatter):
    if scatter:
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        data = XyChartData()
        data.add_series("Observations").add_data_point(10, 20)
        shape = slide.shapes.add_chart(
            XL_CHART_TYPE.XY_SCATTER, Inches(1), Inches(1), Inches(5), Inches(4), data
        )
        shape.chart.has_title = True
        shape.chart.chart_title.text_frame.text = "Old title"
    else:
        presentation, shape = chart_deck()
    tx = shape.chart._chartSpace.xpath("./c:chart/c:title/c:tx")[0]
    for child in list(tx):
        tx.remove(child)
    reference = etree.SubElement(tx, qn("c:strRef"))
    etree.SubElement(reference, qn("c:f")).text = "[unavailable.xlsx]Sheet1!$A$1"
    cache = etree.SubElement(reference, qn("c:strCache"))
    etree.SubElement(cache, qn("c:ptCount"), val="1")
    point = etree.SubElement(cache, qn("c:pt"), idx="0")
    etree.SubElement(point, qn("c:v")).text = "Cached title"
    payload = save(presentation)
    source = BytesIO(payload)

    elements = partition_pptx(file=source, languages=["eng"])

    assert elements[0].text == "Cached title"
    assert isinstance(elements[0], Title)
    assert source.getvalue() == payload
