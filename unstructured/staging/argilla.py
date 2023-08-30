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
    XML = "xml" # TODO: WIP
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
    "defaults": [
        TextField(name="filename", use_markdown=True),
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
    ):
    """
    Creates a FeedbackDataset for Argilla based on the partition type and questions.

    Args:
        partition_type (Union[str, ARGILLA_PARTITION_TYPES]): The partition type to use.
        questions (List[Union[TextQuestion, LabelQuestion, MultiLabelQuestion, RankingQuestion, RatingQuestion]]): The questions to use.

    Returns:
        FeedbackDataset: The FeedbackDataset for Argilla.
    """
    partition_type = ARGILLA_PARTITION_TYPES(partition_type)
    fields = [TextField(name="filename", use_markdown=True)]
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

def _get_metadata_from_elements(elements: List[Text]) -> dict:
    """
    Gets the metadata from a list of elements.

    Args:
        elements (List[Text]): The elements to get the metadata from.

    Returns:
        dict: The metadata.
    """
    metadata_list = {}
    for element in elements:
        metadata = element.metadata.to_dict()
        for key, value in metadata.items():
            if key in metadata_list:
                metadata_list[key].append(value)
            else:
                metadata_list[key] = [value]

    return metadata_list



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

def _partition_iterator(files, partition_funcs, **partition_kwargs):
    """ Helper function to iterate over partitions. """
    for partition_func, filename in zip(partition_funcs, files):
        yield partition_func(filename=filename, **partition_kwargs)


def partition_stage_for_argilla(
    dataset: FeedbackDataset,
    partition_types: Union[str, List[str]],
    files: Union[str, List[str]],
    include_metadata: bool = True,
    partition_kwargs: dict = {},
    chunk_by: Optional[Union[str, bool, list]] = None,
    join_operator: Optional[str] = "\n",
    batch_size: int = 100,
    post_processing_func: Optional[callable] = lambda x: x,
) -> FeedbackDataset:
    """
    Stages a FeedbackDataset for Argilla based on the partition type and questions.

    Args:
        dataset (FeedbackDataset): The FeedbackDataset to stage.
        partition_type (Union[str, List[str]]): The partition type to use per file
        files (Union[str, List[str]]): The files to use.
        partition_kwargs (dict, optional): The partition kwargs to use. Defaults to {}.
        include_metadata (bool, optional): Whether to include metadata. Defaults to True.
        chunk_by (Optional[Union[str, bool, list]], optional): The chunk strategy to use.
            Possible options are ["title", "element_type", "page"]. Defaults to None.
        join_operator (Optional[str], optional): The join operator to use. Defaults to "\n".
        batch_size (int, optional): The batch size to use. Defaults to 100.
        post_processing_func (Optional[callable], optional): The post processing function to use. Defaults to lambda x: x.

    Returns:
        FeedbackDataset: The FeedbackDataset for Argilla.
    """
    if isinstance(files, str):
        files = [files]
    if isinstance(partition_types, str):
        partition_types = [partition_types] * len(files)
    elif isinstance(partition_types, list):
        if len(partition_types) != len(files):
            raise ValueError("The length of `partition_type` must be the same as the length of `files`.")
    partition_types = [ARGILLA_PARTITION_TYPES(partition_type) for partition_type in partition_types]


    # check if all partition types are the same group
    if len(set([TYPE_TO_GROUP[partition_type] for partition_type in partition_types])) > 1:
        raise ValueError("All partition types must be of the same group.")
    else:
        partition_group = TYPE_TO_GROUP[partition_types[0]]

    # check if chunk_by is valid
    if partition_group in ["text_without_pages", "text_with_pages"]:
        if chunk_by is None:
            warnings.warn("No `chunk_by`. Using ['title'] as a default. Set `group_by=False` if no groupby is intended.`")
            chunk_by = ["title"]
    else:
        if chunk_by:
            warnings.warn(f"You passed `group_by` but {partition_types} is a single page document.")

    records = []
    partition_funcs = [_get_partition_func(parition_type) for parition_type in partition_types]
    elements_iterator = _partition_iterator(files, partition_funcs, **partition_kwargs)
    for elements in elements_iterator:
        fields, metadata = {}, {}
        if elements:
            fields = {"filename": elements[0].metadata.filename}

        if partition_group == "email":
            metadata = _get_metadata_from_elements(elements)if include_metadata else {}
            elements = _convert_elements_to_text(elements)
            fields.update({
                "sent_from": metadata.get("sent_from"),
                "sent_to": metadata.get("sent_to"),
                "subject": metadata.get("subject"),
                "text": "\n".join(elements),
            })
            fields = _ensure_string_values_dict(fields)
            records.append(FeedbackRecord(fields=fields, metadata=metadata))
        elif partition_group in ["tables_without_pages", "tables_with_pages"]:
            for element in elements:
                metadata = _get_metadata_from_elements([elements]) if metadata else {}
                fields.update({
                    "page_id": metadata.get("page_name"),
                    "table": join_operator.join(_convert_elements_to_text([element], as_html=True)),
                    "table_as_text": join_operator.join(_convert_elements_to_text([element], as_html=False)),
                })
                if partition_group == "tables_without_pages":
                    del fields["page_id"]
                else:
                    del fields["table_as_text"]
                fields = _ensure_string_values_dict(fields)
                records.append(FeedbackRecord(fields=fields, metadata=metadata))
        elif partition_group == "slides":
            page_elements = {}
            for element in elements:
                last_page = 1
                if element.metadata.page_number:
                    last_page = element.metadata.page_number
                if last_page not in page_elements:
                    page_elements[last_page] = []
                page_elements[last_page].append(element)
            for page_number, page_elements in page_elements.items():
                metadata = _get_metadata_from_elements(page_elements)if include_metadata else {}
                fields.update({"page_id": page_number})
                if not page_elements:
                    continue
                if isinstance(page_elements[0], Title):
                    fields["title"] = page_elements[0].text
                    page_elements = page_elements[1:]
                fields["content"] = join_operator.join(
                    _convert_elements_to_text(page_elements)
                )
                records.append(FeedbackRecord(fields=fields, metadata=metadata))
        elif partition_group in ["text_with_pages", "text_without_pages"]:
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

            if chunk_by:
                df = df.groupby(by=chunk_by, sort=False, as_index=False).agg(list)
            else:
                df.element = df.element.apply(lambda x: [x])

            df.metadata = df.element.apply(lambda x: _get_metadata_from_elements(x) if include_metadata else {})
            df.element = df.element.apply(lambda x: "\n".join(_convert_elements_to_text(x)).strip())

            metadata_list = df.metadata.tolist()
            for item in df.to_dict(orient="records"):
                fields.update({
                    "page_id": item.get("page", [1]),
                    "title": item.get("title"),
                    "element_type": item.get("element_type"),
                    "text": item.get("element").lstrip(item.get("title"))
                })
                fields = _ensure_string_values_dict(fields)
                if partition_group == "text_without_pages":
                    del fields["page_id"]
                records.append(FeedbackRecord(fields=fields, metadata=metadata_list.pop()))
        elif partition_group == "text_with_dom":
            raise NotImplementedError("We do not support DOM yet. Feel free to open an issue on GitHub.")
        elif partition_group == "api":
            raise NotImplementedError("We do not support the API yet. Feel free to open an issue on GitHub.")
        else:
            raise ValueError(f"Invalid partition type: {partition_types}")

        if len(records) > batch_size:
            dataset.add_records(post_processing_func(records))
            records = []

    if records:
        dataset.add_records(post_processing_func(records))

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
