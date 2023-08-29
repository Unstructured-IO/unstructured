import warnings
from enum import Enum
from typing import List, Optional, Union

import argilla
import pandas as pd
from argilla.client.models import (
    Text2TextRecord,
    TextClassificationRecord,
    TokenClassificationRecord,
)
from argilla.feedback import (
    FeedbackDataset,
    FeedbackRecord,
    LabelQuestion,
    MultiLabelQuestion,
    RankingQuestion,
    RatingQuestion,
    TextField,
    TextQuestion,
)

from unstructured.documents.elements import Text, Title
from unstructured.nlp.tokenize import word_tokenize


class ARGILLA_PARTITION_TYPES(Enum):
    # EMAIL
    MSG = "msg"
    EML = "eml"
    EMAIL = "email"
    # SLIDES
    PPT = "ppt"
    PPTX = "pptx"
    # TABLES WITH PAGES
    XLS = "xls"
    XLSX = "xlsx"
    # TABLES WITHOUT PAGES
    TSV = "tsv"
    CSV = "csv"
    # TEXT with pages
    PDF = "pdf"
    EPUB = "epub"
    DOC = "doc"
    DOCX = "docx"
    # TEXT without pages
    ODT = "odt"
    ORG = "org"
    MD = "md"
    TXT = "txt"
    TEXT = "text"
    RTF = "rtf"
    RST = "rst"
    IMAGE = "image"
    # TEXT WITH DOM
    HTML = "html" # TODO: WIP
    XML = "xml" # TODO: potentially infer structure from file?
    # API
    API = "api" # TODO: WIP infer knowledge from file type

GROUP_TO_TYPE = {
    "email": [ARGILLA_PARTITION_TYPES.MSG, ARGILLA_PARTITION_TYPES.EML, ARGILLA_PARTITION_TYPES.EMAIL],
    "slides": [ARGILLA_PARTITION_TYPES.PPT, ARGILLA_PARTITION_TYPES.PPTX],
    "tables_with_pages": [ARGILLA_PARTITION_TYPES.XLS, ARGILLA_PARTITION_TYPES.XLSX],
    "tables_without_pages": [ARGILLA_PARTITION_TYPES.TSV, ARGILLA_PARTITION_TYPES.CSV],
    "text_with_pages": [
        ARGILLA_PARTITION_TYPES.PDF, ARGILLA_PARTITION_TYPES.EPUB,
        ARGILLA_PARTITION_TYPES.DOC, ARGILLA_PARTITION_TYPES.DOCX
    ],
    "text_without_pages": [
        ARGILLA_PARTITION_TYPES.TXT, ARGILLA_PARTITION_TYPES.TEXT,
        ARGILLA_PARTITION_TYPES.RTF, ARGILLA_PARTITION_TYPES.RST,
        ARGILLA_PARTITION_TYPES.IMAGE, ARGILLA_PARTITION_TYPES.ODT,
        ARGILLA_PARTITION_TYPES.ORG, ARGILLA_PARTITION_TYPES.MD,
    ],
    "text_with_dom": [ARGILLA_PARTITION_TYPES.HTML, ARGILLA_PARTITION_TYPES.XML],
    "api": [ARGILLA_PARTITION_TYPES.API],
}

TYPE_TO_GROUP = {value: key for key, values in GROUP_TO_TYPE.items() for value in values}

GROUP_TO_FIELDS = {
    "defaults": [ # TODO: do we want to include defaults?
        TextField(name="element_id", use_markdown=True),
        TextField(name="filename", use_markdown=True),
        TextField(name="last_modified", use_markdown=True),
        TextField(name="filetype", use_markdown=True),
    ],
    "email": [
        TextField(name="sent_from", use_markdown=True),
        TextField(name="sent_to", use_markdown=True),
        TextField(name="subject", use_markdown=True),
        TextField(name="text", use_markdown=True),
    ],
    "slides": [
        TextField(name="page_id", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="content", use_markdown=True),
    ],
    "tables_with_pages": [
        TextField(name="page_id", use_markdown=True),
        TextField(name="table", use_markdown=True),
    ],
    "tables_without_pages": [
        TextField(name="table", use_markdown=True),
        TextField(name="table_as_text", use_markdown=True),
    ],
    "text_with_pages": [
        TextField(name="page_id", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="element_type", use_markdown=True),
        TextField(name="text", use_markdown=True, required=False),
    ],
    "text_without_pages": [
        TextField(name="title", use_markdown=True),
        TextField(name="element_type", use_markdown=True),
        TextField(name="text", use_markdown=True, required=False),
    ],
    "text_with_dom": [
        TextField(name="head", use_markdown=True),
        TextField(name="body", use_markdown=True),
        TextField(name="scripts", use_markdown=True),
    ],
    "api": [
        TextField(name="api", use_markdown=True),
    ]
}

def _get_partition_func(partition_type: ARGILLA_PARTITION_TYPES):
    if partition_type == ARGILLA_PARTITION_TYPES.MSG:
        from unstructured.partition.msg import partition_msg as partition_func
    elif partition_type in [ARGILLA_PARTITION_TYPES.EML, ARGILLA_PARTITION_TYPES.EMAIL]:
        from unstructured.partition.email import partition_email as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.TSV:
        from unstructured.partition.tsv import partition_tsv as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.CSV:
        from unstructured.partition.csv import partition_csv as partition_func
    elif partition_type in [ARGILLA_PARTITION_TYPES.XLS, ARGILLA_PARTITION_TYPES.XLSX]:
        from unstructured.partition.xlsx import partition_xlsx as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.PPT:
        from unstructured.partition.ppt import partition_ppt as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.PPTX:
        from unstructured.partition.pptx import partition_pptx as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.PDF:
        from unstructured.partition.pdf import partition_pdf as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.EPUB:
        from unstructured.partition.epub import partition_epub as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.DOC:
        from unstructured.partition.doc import partition_doc as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.DOCX:
        from unstructured.partition.docx import partition_docx as partition_func
    elif partition_type in [ARGILLA_PARTITION_TYPES.TXT, ARGILLA_PARTITION_TYPES.TEXT]:
        from unstructured.partition.text import partition_text as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.MD:
        from unstructured.partition.md import partition_md as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.RTF:
        from unstructured.partition.rtf import partition_rtf as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.RST:
        from unstructured.partition.rst import partition_rst as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.IMAGE:
        from unstructured.partition.image import partition_image as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.HTML:
        from unstructured.partition.html import partition_html as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.XML:
        from unstructured.partition.xml import partition_xml as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.ODT:
        from unstructured.partition.odt import partition_odt as partition_func
    elif partition_type == ARGILLA_PARTITION_TYPES.ORG:
        from unstructured.partition.org import partition_org as partition_func
    else:
        raise ValueError(f"Invalid partition type: {partition_type}")
    return partition_func


def get_argilla_feedback_dataset(
        partition_type: Union[str, ARGILLA_PARTITION_TYPES],
        questions: List[Union[TextQuestion, LabelQuestion, MultiLabelQuestion, RankingQuestion, RatingQuestion]],
        include_defaults: Optional[bool] = True,
    ):
    """
    Creates a FeedbackDataset for Argilla based on the partition type and questions.

    Args:
        partition_type (Union[str, ARGILLA_PARTITION_TYPES]): The partition type to use.
        questions (List[Union[TextQuestion, LabelQuestion, MultiLabelQuestion, RankingQuestion, RatingQuestion]]): The questions to use.
        include_defaults (Optional[bool], optional): Whether to include the default fields. Defaults to True.

    Returns:
        FeedbackDataset: The FeedbackDataset for Argilla.
    """

    # TODO: do we want to default to a TextQuestion?
    partition_type = ARGILLA_PARTITION_TYPES(partition_type)
    fields = GROUP_TO_FIELDS["defaults"] if include_defaults else []
    fields += GROUP_TO_FIELDS[TYPE_TO_GROUP[partition_type]]

    return FeedbackDataset(
        fields=fields,
        questions=questions,
    )

def _ensure_string_values_dict(dictionary: dict) -> dict:
    """
    Ensures that all values in a dictionary are strings.

    Args:
        dictionary (dict): The dictionary to convert.
    """
    return {key: str(value) for key, value in dictionary.items()}

def _convert_elements_to_text(elements: List[Text], as_html: bool = True) -> List[str]:
    """
    Converts a list of elements to text.

    Args:
        elements (List[Text]): The elements to convert.
        as_html (bool, optional): Whether to return the text as html. Defaults to True.

    Returns:
        List[str]: The text.
    """
    text = []
    for element in elements:
        if element.metadata.text_as_html and as_html:
            text.append(element.metadata.text_as_html)
        else:
            text.append(element.text)
    return text

def _partition_iterator(files, partition_func, **partition_kwargs):
    """ Helper function to iterate over partitions. """
    for filename in files:
        yield partition_func(filename=filename, **partition_kwargs)


def stage_for_argilla_feedback(
    partition_type: str,
    dataset: FeedbackDataset,
    files: Union[str, List[str]],
    partition_kwargs: dict = {},
    group_by: Optional[Union[str, bool, list]] = None,
    join_operator: Optional[str] = "\n",
):
    partition_type = ARGILLA_PARTITION_TYPES(partition_type)
    if partition_type in GROUP_TO_TYPE["text_without_pages"] + GROUP_TO_TYPE["text_with_pages"]:
        if group_by is None:
            warnings.warn("No `group_by`. Using ['title'] as a default. Set `group_by=False` if no groupby is intended.`")
            group_by = ["title"]
    else:
        if group_by:
            warnings.warn(f"You passed `group_by` but {partition_type} is a single page document.")


    records = []
    partition_func = _get_partition_func(partition_type)
    if isinstance(files, str):
        files = [files]
    elements_iterator = _partition_iterator(files, partition_func, **partition_kwargs)
    for elements in elements_iterator:
        if partition_type in GROUP_TO_TYPE["email"]:
            # TODO: What happens when there are multiple emails in the .msg-file?
            metadata = elements[0].metadata.to_dict()
            elements = _convert_elements_to_text(elements)
            fields = {
                "sent_from": metadata.get("sent_from"),
                "sent_to": metadata.get("sent_to"),
                "subject": metadata.get("subject"),
                "text": "\n".join(elements),
            }
            fields = _ensure_string_values_dict(fields)
            records.append(FeedbackRecord(fields=fields))
        elif partition_type in GROUP_TO_TYPE["tables_without_pages"] + GROUP_TO_TYPE["tables_with_pages"]:
            for element in elements:
                metadata = element.metadata.to_dict()
                fields = {
                    "page_id": metadata.get("page_name"),
                    "table": join_operator.join(_convert_elements_to_text([element], as_html=True)),
                    "table_as_text": join_operator.join(_convert_elements_to_text([element], as_html=False)),
                }
                if partition_type in GROUP_TO_TYPE["tables_without_pages"]:
                    del fields["page_id"]
                else:
                    del fields["table_as_text"]
                fields = _ensure_string_values_dict(fields)
                records.append(FeedbackRecord(fields=fields))
        elif partition_type in GROUP_TO_TYPE["slides"]:
            page_elements = {}
            for element in elements:
                last_page = 1
                if element.metadata.page_number:
                    last_page = element.metadata.page_number
                if last_page not in page_elements:
                    page_elements[last_page] = []
                page_elements[last_page].append(element)
            for page_number, page_elements in page_elements.items():
                fields = {
                    "page_id": page_number,
                }
                if not page_elements:
                    continue
                if isinstance(page_elements[0], Title):
                    fields["title"] = page_elements[0].text
                    page_elements = page_elements[1:]
                fields["content"] = join_operator.join(
                    _convert_elements_to_text(page_elements)
                )
                records.append(FeedbackRecord(fields=fields))
        elif partition_type in GROUP_TO_TYPE["text_with_pages"] + GROUP_TO_TYPE["text_without_pages"]:
            last_title = "None"
            page_last = 1
            element_overview = []
            for element in elements:
                if isinstance(element, Title):
                    last_title = element.text
                page_last = element.metadata.page_number or page_last
                element_overview.append({
                    "title": last_title,
                    "element_type": element.to_dict().get("type"),
                    "page": page_last,
                    "element": element
                })
            df = pd.DataFrame(element_overview)

            if group_by:
                df = df.groupby(by=group_by, sort=False, as_index=False).agg(list)
            else:
                df.element = df.element.apply(lambda x: [x])
            df.element = df.element.apply(lambda x: "\n".join(_convert_elements_to_text(x)).strip())

            for item in df.to_dict(orient="records"):
                fields = {
                    "page_id": item.get("page", [1]),
                    "title": item.get("title"),
                    "element_type": item.get("element_type"),
                    "text": item.get("element").lstrip(item.get("title"))
                }
                fields = _ensure_string_values_dict(fields)
                if partition_type in [ARGILLA_PARTITION_TYPES.TXT]:
                    del fields["page_id"]
                records.append(FeedbackRecord(fields=fields))
        elif partition_type in GROUP_TO_TYPE["text_with_dom"]:
            raise NotImplementedError("TODO: implement")
        elif partition_type in GROUP_TO_TYPE["api"]:
            raise NotImplementedError("TODO: implement")
        else:
            raise ValueError(f"Invalid partition type: {partition_type}")
        # TODO: add batched option?
    dataset.add_records(records)

    return dataset

def stage_for_argilla(
    elements: List[Text],
    argilla_task: str,
    **record_kwargs,
) -> Union[
    argilla.DatasetForTextClassification,
    argilla.DatasetForTokenClassification,
    argilla.DatasetForText2Text,
]:
    ARGILLA_TASKS = {
        "text_classification": (TextClassificationRecord, argilla.DatasetForTextClassification),
        "token_classification": (TokenClassificationRecord, argilla.DatasetForTokenClassification),
        "text2text": (Text2TextRecord, argilla.DatasetForText2Text),
    }

    try:
        argilla_record_class, argilla_dataset_class = ARGILLA_TASKS[argilla_task]
    except KeyError as e:
        raise ValueError(
            f'Invalid value "{e.args[0]}" specified for argilla_task. '
            "Must be one of: {', '.join(ARGILLA_TASKS.keys())}.",
        )

    for record_kwarg_key, record_kwarg_value in record_kwargs.items():
        if type(record_kwarg_value) is not list or len(record_kwarg_value) != len(elements):
            raise ValueError(
                f'Invalid value specified for "{record_kwarg_key}" keyword argument.'
                " Must be of type list and same length as elements list.",
            )

    results: List[Union[TextClassificationRecord, TokenClassificationRecord, Text2TextRecord]] = []

    for idx, element in enumerate(elements):
        element_kwargs = {kwarg: record_kwargs[kwarg][idx] for kwarg in record_kwargs}
        arguments = dict(**element_kwargs, text=element.text)
        if isinstance(element.id, str):
            arguments["id"] = element.id

        # NOTE(robinson) - TokenClassificationRecord raises and error if tokens are not
        # provided as part of the input for the record. Default to the nltk word tokenizer
        if argilla_task == "token_classification" and "tokens" not in arguments:
            tokens = word_tokenize(arguments["text"])
            arguments["tokens"] = tokens

        results.append(argilla_record_class(**arguments))

    return argilla_dataset_class(results)
