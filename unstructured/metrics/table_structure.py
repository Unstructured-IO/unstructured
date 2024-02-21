import numpy as np
import pandas as pd
from PIL import Image

from unstructured.partition.pdf import convert_pdf_to_images
from unstructured.partition.pdf_image.ocr import get_table_tokens
from unstructured.utils import requires_dependencies


@requires_dependencies("unstructured_inference")
def image_or_pdf_to_dataframe(filename: str) -> pd.DataFrame:
    """helper to JUST run table transformer on the input image/pdf file. It assumes the input is
    JUST a table. This is intended to facilitate metric tracking on table structure detection ALONE
    without mixing metric of element detection model"""
    from unstructured_inference.models.tables import load_agent, tables_agent

    load_agent()

    if filename.endswith(".pdf"):
        image = list(convert_pdf_to_images(filename))[0].convert("RGB")
    else:
        image = Image.open(filename).convert("RGB")

    return tables_agent.run_prediction(
        image, ocr_tokens=get_table_tokens(image), result_format="dataframe"
    )


@requires_dependencies("unstructured_inference")
def eval_table_transformer_for_file(
    filename: str,
    true_table_filename: str,
    eval_func: str = "token_ratio",
) -> float:
    """evaluate the predicted table structure vs. actual table structure by column and row as a
    number between 0 and 1"""
    from unstructured_inference.models.eval import compare_contents_as_df

    pred_table = image_or_pdf_to_dataframe(filename).fillna("").replace(np.nan, "")
    actual_table = pd.read_csv(true_table_filename).astype(str).fillna("").replace(np.nan, "")

    results = np.array(
        list(compare_contents_as_df(actual_table, pred_table, eval_func=eval_func).values()),
    )
    return results.mean() / 100.0
