import pytest

from unstructured.partition.html import partition_html


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("<mi>x</mi><mo>+</mo><mn>2</mn>", "x+2"),
        ("<mfrac><mi>a</mi><mi>b</mi></mfrac>", r"\frac{a}{b}"),
        (
            "<mfrac><mrow><mn>1</mn><mo>+</mo><msqrt><mn>5</mn></msqrt></mrow><mn>2</mn></mfrac>",
            r"\frac{1+\sqrt{5}}{2}",
        ),
        ("<mroot><mi>x</mi><mn>3</mn></mroot>", r"\sqrt[3]{x}"),
        ("<msup><mi>x</mi><mn>2</mn></msup>", r"{x}^{2}"),
        ("<msub><mi>x</mi><mi>i</mi></msub>", r"{x}_{i}"),
        ("<msubsup><mi>x</mi><mi>i</mi><mn>2</mn></msubsup>", r"{x}_{i}^{2}"),
        ("<mover><mi>x</mi><mo>¯</mo></mover>", r"\overset{¯}{x}"),
        ("<munder><mo>lim</mo><mi>x</mi></munder>", r"\underset{x}{lim}"),
        (
            "<munderover><mo>∑</mo><mi>i</mi><mi>n</mi></munderover>",
            r"\overset{n}{\underset{i}{∑}}",
        ),
        ('<mfenced open="[" close="]" separators=";"><mi>x</mi><mi>y</mi></mfenced>', "[x;y]"),
        (
            "<mtable><mtr><mtd><mn>1</mn></mtd><mtd><mn>2</mn></mtd></mtr>"
            "<mtr><mtd><mn>3</mn></mtd><mtd><mn>4</mn></mtd></mtr></mtable>",
            r"\begin{matrix}1 & 2 \\ 3 & 4\end{matrix}",
        ),
        ("<mi>x</mi><mo>=</mo><mtext>50% &amp; rising</mtext>", r"x=\text{50\% \& rising}"),
        (
            "<semantics><msup><mi>x</mi><mn>2</mn></msup>"
            '<annotation encoding="application/other">do not duplicate</annotation></semantics>',
            r"{x}^{2}",
        ),
    ],
)
def test_presentation_mathml_is_retained_without_a_tex_annotation(expression, expected):
    elements = partition_html(
        text=f"<p>Value <math>{expression}</math> remains.</p>", languages=["eng"]
    )

    assert [element.text for element in elements] == [f"Value {expected} remains."]


def test_presentation_mathml_preserves_display_boundary_and_page_number():
    html = (
        '<div data-page-number="3">Before<math display="block">'
        "<mfrac><mi>x</mi><mn>2</mn></mfrac></math>After</div>"
    )

    elements = partition_html(text=html, languages=["eng"])

    assert [element.text for element in elements] == ["Before", r"\frac{x}{2}", "After"]
    assert [element.metadata.page_number for element in elements] == [3, 3, 3]


@pytest.mark.parametrize(
    "expression",
    [
        "<mfrac><mi>x</mi></mfrac>",
        "<mrow><mi>x</mi><maction><mi>y</mi></maction></mrow>",
        '<mfrac linethickness="0"><mi>x</mi><mi>y</mi></mfrac>',
    ],
)
def test_unsupported_or_malformed_math_keeps_existing_visual_fallback(expression):
    html = (
        '<p><span class="katex"><span class="katex-mathml">'
        f"<math>{expression}</math></span>"
        '<span class="katex-html">Visual fallback</span></span></p>'
    )

    assert partition_html(text=html, languages=["eng"])[0].text == "Visual fallback"
