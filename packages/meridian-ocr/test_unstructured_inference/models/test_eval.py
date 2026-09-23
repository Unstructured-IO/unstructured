import pytest

from unstructured_inference.inference.layoutelement import table_cells_to_dataframe
from unstructured_inference.models.eval import compare_contents_as_df, default_tokenizer


@pytest.fixture
def actual_cells():
    return [
        {
            "column_nums": [0],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Disability Category",
        },
        {
            "column_nums": [1],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Participants",
        },
        {
            "column_nums": [2],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Ballots Completed",
        },
        {
            "column_nums": [3],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Ballots Incomplete/Terminated",
        },
        {"column_nums": [4, 5], "row_nums": [0], "column header": True, "cell text": "Results"},
        {"column_nums": [4], "row_nums": [1], "column header": False, "cell text": "Accuracy"},
        {
            "column_nums": [5],
            "row_nums": [1],
            "column header": False,
            "cell text": "Time to complete",
        },
        {"column_nums": [0], "row_nums": [2], "column header": False, "cell text": "Blind"},
        {"column_nums": [0], "row_nums": [3], "column header": False, "cell text": "Low Vision"},
        {"column_nums": [0], "row_nums": [4], "column header": False, "cell text": "Dexterity"},
        {"column_nums": [0], "row_nums": [5], "column header": False, "cell text": "Mobility"},
        {"column_nums": [1], "row_nums": [2], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [3], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [4], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [5], "column header": False, "cell text": "3"},
        {"column_nums": [2], "row_nums": [2], "column header": False, "cell text": "1"},
        {"column_nums": [2], "row_nums": [3], "column header": False, "cell text": "2"},
        {"column_nums": [2], "row_nums": [4], "column header": False, "cell text": "4"},
        {"column_nums": [2], "row_nums": [5], "column header": False, "cell text": "3"},
        {"column_nums": [3], "row_nums": [2], "column header": False, "cell text": "4"},
        {"column_nums": [3], "row_nums": [3], "column header": False, "cell text": "3"},
        {"column_nums": [3], "row_nums": [4], "column header": False, "cell text": "1"},
        {"column_nums": [3], "row_nums": [5], "column header": False, "cell text": "0"},
        {"column_nums": [4], "row_nums": [2], "column header": False, "cell text": "34.5%, n=1"},
        {
            "column_nums": [4],
            "row_nums": [3],
            "column header": False,
            "cell text": "98.3% n=2 (97.7%, n=3)",
        },
        {"column_nums": [4], "row_nums": [4], "column header": False, "cell text": "98.3%, n=4"},
        {"column_nums": [4], "row_nums": [5], "column header": False, "cell text": "95.4%, n=3"},
        {"column_nums": [5], "row_nums": [2], "column header": False, "cell text": "1199 sec, n=1"},
        {
            "column_nums": [5],
            "row_nums": [3],
            "column header": False,
            "cell text": "1716 sec, n=3 (1934 sec, n=2)",
        },
        {
            "column_nums": [5],
            "row_nums": [4],
            "column header": False,
            "cell text": "1672.1 sec, n=4",
        },
        {"column_nums": [5], "row_nums": [5], "column header": False, "cell text": "1416 sec, n=3"},
    ]


@pytest.fixture
def pred_cells():
    return [
        {"column_nums": [0], "row_nums": [2], "column header": False, "cell text": "Blind"},
        {"column_nums": [0], "row_nums": [3], "column header": False, "cell text": "Low Vision"},
        {"column_nums": [0], "row_nums": [4], "column header": False, "cell text": "Dexterity"},
        {"column_nums": [0], "row_nums": [5], "column header": False, "cell text": "Mobility"},
        {"column_nums": [1], "row_nums": [2], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [3], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [4], "column header": False, "cell text": "5"},
        {"column_nums": [1], "row_nums": [5], "column header": False, "cell text": "3"},
        {"column_nums": [2], "row_nums": [2], "column header": False, "cell text": "1"},
        {"column_nums": [2], "row_nums": [3], "column header": False, "cell text": "2"},
        {"column_nums": [2], "row_nums": [4], "column header": False, "cell text": "4"},
        {"column_nums": [2], "row_nums": [5], "column header": False, "cell text": "3"},
        {"column_nums": [3], "row_nums": [2], "column header": False, "cell text": "4"},
        {"column_nums": [3], "row_nums": [3], "column header": False, "cell text": "3"},
        {"column_nums": [3], "row_nums": [4], "column header": False, "cell text": "1"},
        {"column_nums": [3], "row_nums": [5], "column header": False, "cell text": "0"},
        {"column_nums": [4], "row_nums": [1], "column header": False, "cell text": "Accuracy"},
        {"column_nums": [4], "row_nums": [2], "column header": False, "cell text": "34.5%, n=1"},
        {
            "column_nums": [4],
            "row_nums": [3],
            "column header": False,
            "cell text": "98.3% n=2 (97.7%, n=3)",
        },
        {"column_nums": [4], "row_nums": [4], "column header": False, "cell text": "98.3%, n=4"},
        {"column_nums": [4], "row_nums": [5], "column header": False, "cell text": "95.4%, n=3"},
        {
            "column_nums": [5],
            "row_nums": [1],
            "column header": False,
            "cell text": "Time to complete",
        },
        {"column_nums": [5], "row_nums": [2], "column header": False, "cell text": "1199 sec, n=1"},
        {
            "column_nums": [5],
            "row_nums": [3],
            "column header": False,
            "cell text": "1716 sec, n=3 | (1934 sec, n=2)",
        },
        {
            "column_nums": [5],
            "row_nums": [4],
            "column header": False,
            "cell text": "1672.1 sec, n=4",
        },
        {"column_nums": [5], "row_nums": [5], "column header": False, "cell text": "1416 sec, n=3"},
        {
            "column_nums": [0],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "soa etealeiliay Category",
        },
        {"column_nums": [4, 5], "row_nums": [0], "column header": True, "cell text": "Results"},
        {
            "column_nums": [1],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Participants P",
        },
        {
            "column_nums": [2],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "pallets Completed",
        },
        {
            "column_nums": [3],
            "row_nums": [0, 1],
            "column header": True,
            "cell text": "Ballot: incom lete/ Ne Terminated",
        },
    ]


@pytest.fixture
def actual_df(actual_cells):
    return table_cells_to_dataframe(actual_cells).fillna("")


@pytest.fixture
def pred_df(pred_cells):
    return table_cells_to_dataframe(pred_cells).fillna("")


@pytest.mark.parametrize(
    ("eval_func", "processor"),
    [
        ("token_ratio", default_tokenizer),
        ("token_ratio", None),
        ("partial_token_ratio", default_tokenizer),
        ("ratio", None),
        ("ratio", default_tokenizer),
        ("partial_ratio", default_tokenizer),
    ],
)
def test_compare_content_as_df(actual_df, pred_df, eval_func, processor):
    results = compare_contents_as_df(actual_df, pred_df, eval_func=eval_func, processor=processor)
    assert 0 < results.get(f"by_col_{eval_func}") < 100


def test_compare_content_as_df_with_invalid_input(actual_df, pred_df):
    with pytest.raises(ValueError, match="eval_func must be one of"):
        compare_contents_as_df(actual_df, pred_df, eval_func="foo")
