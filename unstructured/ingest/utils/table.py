import typing as t

import pandas as pd

from unstructured.staging.base import flatten_dict, get_default_pandas_dtypes


def convert_to_pandas_dataframe(
    elements_dict: t.List[t.Dict[str, t.Any]],
    drop_empty_cols: bool = False,
) -> pd.DataFrame:
    # Flatten metadata if it hasn't already been flattened
    for d in elements_dict:
        if metadata := d.pop("metadata", None):
            d.update(flatten_dict(metadata, keys_to_omit=["data_source_record_locator"]))

    df = pd.DataFrame.from_dict(
        elements_dict,
    )
    dt = {k: v for k, v in get_default_pandas_dtypes().items() if k in df.columns}
    df = df.astype(dt)
    if drop_empty_cols:
        df.dropna(axis=1, how="all", inplace=True)
    return df
