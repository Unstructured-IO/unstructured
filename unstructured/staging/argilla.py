from typing import List, Union

import argilla
from argilla.client.models import (
    Text2TextRecord,
    TextClassificationRecord,
    TokenClassificationRecord,
)

from unstructured.documents.elements import Text
from unstructured.nlp.tokenize import word_tokenize


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
