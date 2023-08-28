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
    # SLIDES
    PPT = "ppt"
    PPTX = "pptx"
    # TABLES
    TSV = "tsv"
    CSV = "csv"
    XLS = "xls"
    XLSX = "xlsx"
    # TEXT with pages
    PDF = "pdf" # TODO: WIP
    EPUB = "epub" # TODO: WIP
    DOC = "doc" # TODO: WIP
    # TEXT without pages
    ODT = "odt" # TODO: WIP
    ORG = "org" # TODO: WIP
    MD = "md" # TODO: WIP
    TXT = "txt" # TODO: WIP
    RTF = "rtf" # TODO: WIP
    RST = "rst" # TODO: WIP
    IMAGE = "image"
    # TEXT WITH DOM
    HTML = "html" # TODO: WIP
    XML = "xml" # TODO: potentially infer structure from file?
    # API
    API = "api" # TODO: WIP infer knowledge from file type

PARTITION_DATASET_FIELDS = {
    # DEFAULT
    "defaults": [ # TODO: do we want to include defaults?
        TextField(name="element_id", use_markdown=True),
        TextField(name="filename", use_markdown=True),
        TextField(name="last_modified", use_markdown=True),
        TextField(name="filetype", use_markdown=True),
    ],
    # EMAIL
    ARGILLA_PARTITION_TYPES.MSG: [
        TextField(name="sent_from", use_markdown=True),
        TextField(name="sent_to", use_markdown=True),
        TextField(name="subject", use_markdown=True),
        TextField(name="text", use_markdown=True),
        TextField(name="text_with_sep", use_markdown=True)
    ],
    ARGILLA_PARTITION_TYPES.EML: [
        TextField(name="sent_from", use_markdown=True),
        TextField(name="sent_to", use_markdown=True),
        TextField(name="subject", use_markdown=True),
        TextField(name="text", use_markdown=True),
        TextField(name="text_with_sep", use_markdown=True)
    ],
    # TABLES
     ARGILLA_PARTITION_TYPES.CSV: [
        TextField(name="table", use_markdown=True),
        TextField(name="raw_csv", use_markdown=True),
    ],
    ARGILLA_PARTITION_TYPES.TSV: [
        TextField(name="table", use_markdown=True),
        TextField(name="raw_csv", use_markdown=True),
    ],
    ARGILLA_PARTITION_TYPES.XLSX: [
        TextField(name="page_name", use_markdown=True),
        TextField(name="table", use_markdown=True),
    ],
    ARGILLA_PARTITION_TYPES.XLS: [
        TextField(name="page_name", use_markdown=True),
        TextField(name="table", use_markdown=True),
    ],
    # SLIDES
    ARGILLA_PARTITION_TYPES.PPT: [
        TextField(name="page_number", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="content", use_markdown=True),
    ],
    ARGILLA_PARTITION_TYPES.PPTX: [
        TextField(name="page_number", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="content", use_markdown=True),
    ],
    # TEXT with multiple page
    ARGILLA_PARTITION_TYPES.PDF: [
        TextField(name="page_number", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="element_type", use_markdown=True),
        TextField(name="text", use_markdown=True, required=False),
    ],
    ARGILLA_PARTITION_TYPES.DOC: [
        TextField(name="page_number", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="element_type", use_markdown=True),
        TextField(name="text", use_markdown=True, required=False),
    ],
    ARGILLA_PARTITION_TYPES.EPUB: [
        TextField(name="page_number", use_markdown=True),
        TextField(name="title", use_markdown=True),
        TextField(name="element_type", use_markdown=True),
        TextField(name="text", use_markdown=True, required=False),
    ],
    # TEXT with DOM
    ARGILLA_PARTITION_TYPES.HTML: [
        TextField(name="head", use_markdown=True),
        TextField(name="body", use_markdown=True),
        TextField(name="scripts", use_markdown=True),
    ]
}

def get_argilla_feedback_dataset(
        partition_type: Union[str, ARGILLA_PARTITION_TYPES],
        questions: List[Union[TextQuestion, LabelQuestion, MultiLabelQuestion, RankingQuestion, RatingQuestion]],
        include_defaults: Optional[bool] = True,
    ):

    # TODO: do we want to default to a TextQuestion?
    partition_type = ARGILLA_PARTITION_TYPES(partition_type)
    fields = PARTITION_DATASET_FIELDS["defaults"] if include_defaults else []
    fields += PARTITION_DATASET_FIELDS[partition_type]
    return FeedbackDataset(
        fields=fields,
        questions=questions,
    )

def _ensure_string_values_dict(dictionary: dict):
    return {key: str(value) for key, value in dictionary.items()}

def _elements_to_text(elements: List[Text], as_html: bool = True):
    text = []
    for element in elements:
        if element.metadata.text_as_html and as_html:
            text.append(element.metadata.text_as_html)
        else:
            text.append(element.text)
    return text

def _enforce_skipped_field(fields, skip_fields):
    return {key: value for key, value in dict.items() if key not in skip_fields}

def stage_for_argilla_feedback(
    partition_type: str,
    dataset: FeedbackDataset,
    files: Union[str, List[str]],
    sep: str= "\n____________\n",
    partition_kwargs: dict = {},
    # skip_fields: Optional[List[str]] = [], or elements?
    group_by: Optional[str] = None,
):

    if isinstance(files, str):
        files = [files]

    records = []
    partition_type = ARGILLA_PARTITION_TYPES(partition_type)
    if partition_type not in [ARGILLA_PARTITION_TYPES.MSG, ARGILLA_PARTITION_TYPES.EML,
                            ARGILLA_PARTITION_TYPES.CSV]:
        if not group_by:
            warnings.warn(f"You passed `group_by_strategy` but {partition_type} is a single page document.")
    else:
        if group_by:
            warnings.warn("No `group_by_strategy` defined we recommend grouping by `title`, `element_type` and/or `page`. Grouping by ['title', 'element_type'] is a good default.")


    if partition_type in [ARGILLA_PARTITION_TYPES.MSG, ARGILLA_PARTITION_TYPES.EML]:
        # TODO: What happens when there are multiple emails in the .msg-file?
        if partition_type == ARGILLA_PARTITION_TYPES.EML:
            from unstructured.partition.email import partition_email as partition_func
        else:
            from unstructured.partition.msg import partition_msg as partition_func

        for filename in files:
            elements = partition_func(filename=filename, **partition_kwargs)
            metadata = elements[0].metadata.to_dict()
            for elem in elements:
                print(elem.metadata.to_dict())
            elements = _elements_to_text(elements)
            fields = {
                "sent_from": metadata.get("sent_from"),
                "sent_to": metadata.get("sent_to"),
                "subject": metadata.get("subject"),
                "text": "\n".join(elements),
                "text_with_sep": sep.join(elements)
            }
            fields = _ensure_string_values_dict(fields)
            records.append(FeedbackRecord(fields=fields))
    elif partition_type in [ARGILLA_PARTITION_TYPES.CSV, ARGILLA_PARTITION_TYPES.TSV]:
        if partition_type == ARGILLA_PARTITION_TYPES.TSV:
            from unstructured.partition.tsv import partition_tsv as partition_func
        else:
            from unstructured.partition.csv import partition_csv as partition_func

        for filename in files:
            elements = partition_func(filename=filename, **partition_kwargs)
            metadata = elements[0].metadata.to_dict()
            elements_html = _elements_to_text(elements, as_html=True)
            elements_raw = _elements_to_text(elements, as_html=False)
            for element_html, element_raw in zip(elements_html, elements_raw):
                fields = {
                    "table": element_html,
                    "raw_csv": element_raw,
                }
                fields = _ensure_string_values_dict(fields)
                records.append(FeedbackRecord(fields=fields))
    elif partition_type in [ARGILLA_PARTITION_TYPES.PPT , ARGILLA_PARTITION_TYPES.PPTX]:
        if partition_type == ARGILLA_PARTITION_TYPES.PPTX:
            from unstructured.partition.pptx import partition_pptx as partition_func
        else:
            from unstructured.partition.ppt import partition_ppt as partition_func

        for filename in files:
            elements = partition_func(filename=filename, **partition_kwargs)
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
                    "page_number": page_number,
                }
                if not page_elements:
                    continue
                if isinstance(page_elements[0], Title):
                    fields["title"] = page_elements[0].text
                    page_elements = page_elements[1:]
                fields["content"] = "\n".join(
                    _elements_to_text(page_elements)
                )
                records.append(FeedbackRecord(fields=fields))
    elif partition_type in [ARGILLA_PARTITION_TYPES.XLS, ARGILLA_PARTITION_TYPES.XLSX]:
        from unstructured.partition.xlsx import partition_xlsx

        for filename in files:
            elements = partition_xlsx(filename=filename, **partition_kwargs)
            for element in elements:
                fields = {
                    "page_name": element.metadata.page_name,
                    "table": _elements_to_text([element])[0]
                }
                records.append(FeedbackRecord(fields=fields))
    elif partition_type in [ARGILLA_PARTITION_TYPES.PDF, ARGILLA_PARTITION_TYPES.EPUB, ARGILLA_PARTITION_TYPES.DOC]:
        if partition_type == ARGILLA_PARTITION_TYPES.PDF:
            from unstructured.partition.pdf import partition_pdf as partition_func
        elif partition_type == ARGILLA_PARTITION_TYPES.EPUB:
            from unstructured.partition.epub import partition_epub as partition_func
        else:
            from unstructured.partition.doc import partition_doc as partition_func

        for filename in files:
            last_title = "start"
            page_last = 1
            element_overview = []
            elements = partition_func(filename=filename, **partition_kwargs)
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

            df = df.groupby(by=group_by, sort=False, as_index=False).agg(list)
            df.element = df.element.apply(lambda x: "\n".join(_elements_to_text(x)).strip())

            for item in df.to_dict(orient="records"):
                if item.get("title") != "start":
                    fields = {
                        "page_number": item.get("page", [1]),
                        "title": item.get("title"),
                        "element_type": item.get("element_type"),
                        "text": item.get("element").lstrip(item.get("title"))
                    }
                    fields = _ensure_string_values_dict(fields)
                    records.append(FeedbackRecord(fields=fields))

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
