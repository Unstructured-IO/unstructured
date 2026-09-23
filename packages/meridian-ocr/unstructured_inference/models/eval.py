from functools import partial
from typing import Callable, Dict, List, Optional

import pandas as pd
from rapidfuzz import fuzz

EVAL_FUNCTIONS = {
    "token_ratio": fuzz.token_ratio,
    "ratio": fuzz.ratio,
    "partial_token_ratio": fuzz.partial_token_ratio,
    "partial_ratio": fuzz.partial_ratio,
}


def _join_df_content(df, tab_token="\t", row_break_token="\n") -> str:
    """joining dataframe's table content as one long string"""
    return row_break_token.join([tab_token.join(row) for row in df.values])


def default_tokenizer(text: str) -> List[str]:
    """a simple tokenizer that splits text by white space"""
    return text.split()


def compare_contents_as_df(
    actual_df: pd.DataFrame,
    pred_df: pd.DataFrame,
    eval_func: str = "token_ratio",
    processor: Optional[Callable] = None,
    tab_token: str = "\t",
    row_break_token: str = "\n",
) -> Dict[str, float]:
    r"""ravel the table as string then use text distance to compare the prediction against true
    table

    Parameters
    ----------
    actual_df: pd.DataFrame
        actual table as pandas dataframe

    pred_df: pd.DataFrame
        predicted table as pandas dataframe

    eval_func: str, default tp "token_ratio"
        the eval_func should be one of "token_ratio", "ratio", "partial_token_ratio",
        "partial_ratio". Those are functions provided by rapidfuzz to evaluate text distances
        using either tokens or characters. In general token is better than characters for evaluating
        tables.

    processor: Callable, default to None
        processor to tokenize the text; by default None means no processing (using characters). For
        tokens eval functions we recommend using the `default_tokenizer` or some other functions to
        break down the text into words

    tab_token: str, default to "\t"
        the string to join cells together

    row_break_token: str, default to "\n"
        the string to join rows together

    Returns
    -------
    Dict[str, int]
        mapping of by column and by row scores to the scores as float numbers
    """
    func = EVAL_FUNCTIONS.get(eval_func)
    if func is None:
        raise ValueError(
            'eval_func must be one of "token_ratio", "ratio", "partial_token_ratio", '
            f'"partial_ratio" but got {eval_func}',
        )
    join_func = partial(_join_df_content, tab_token=tab_token, row_break_token=row_break_token)
    return {
        f"by_col_{eval_func}": func(
            join_func(actual_df),
            join_func(pred_df),
            processor=processor,
        ),
        f"by_row_{eval_func}": func(
            join_func(actual_df.T),
            join_func(pred_df.T),
            processor=processor,
        ),
    }
