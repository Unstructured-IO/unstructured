from copy import deepcopy
from typing import Callable, List, Optional

from transformers import PreTrainedTokenizer

from unstructured.documents.elements import Element, NarrativeText, Text


def stage_for_transformers(
    elements: List[Text],
    tokenizer: PreTrainedTokenizer,
    **chunk_kwargs,
) -> List[Element]:
    """Stages text elements for transformers pipelines by chunking them into sections that can
    fit into the attention window for the model associated with the tokenizer."""
    chunked_elements: List[Element] = []
    for element in elements:
        # NOTE(robinson) - Only chunk potentially lengthy text. Shorter text (like titles)
        # should already fit into the attention window just fine.
        if isinstance(element, (NarrativeText, Text)):
            chunked_text = chunk_by_attention_window(element.text, tokenizer, **chunk_kwargs)
            for chunk in chunked_text:
                _chunk_element = deepcopy(element)
                _chunk_element.text = chunk
                chunked_elements.append(_chunk_element)
        else:
            chunked_elements.append(element)

    return chunked_elements


def chunk_by_attention_window(
    text: str,
    tokenizer: PreTrainedTokenizer,
    buffer: int = 2,
    max_input_size: Optional[int] = None,
    split_function: Callable[[str], List[str]] = lambda text: text.split(" "),
    chunk_separator: str = " ",
) -> List[str]:
    """Splits a string of text into chunks that will fit into a model's attention
    window.

    Parameters
    ----------
    text: The raw input text for the model
    tokenizer: The transformers tokenizer for the model
    buffer: Indicates the number of tokens to leave as a buffer for the attention window. This
        is to account for special tokens like [CLS] that can appear at the beginning or
        end of an input sequence.
    max_input_size: The size of the attention window for the model. If not specified, will
        use the model_max_length attribute on the tokenizer object.
    split_function: The function used to split the text into chunks to consider for adding to the
        attention window.
    chunk_separator: The string used to concat adjacent chunks when reconstructing the text
    """
    max_input_size = tokenizer.model_max_length if max_input_size is None else max_input_size
    if buffer < 0 or buffer >= max_input_size:
        raise ValueError(
            f"buffer is set to {buffer}. Must be greater than zero and smaller than "
            f"max_input_size, which is {max_input_size}.",
        )

    max_chunk_size = max_input_size - buffer

    split_text: List[str] = split_function(text)
    num_splits = len(split_text)

    chunks: List[str] = []
    chunk_text = ""
    chunk_size = 0

    for i, segment in enumerate(split_text):
        tokens = tokenizer.tokenize(segment)
        num_tokens = len(tokens)
        if num_tokens > max_chunk_size:
            raise ValueError(
                f"The number of tokens in the segment is {num_tokens}. "
                f"The maximum number of tokens is {max_chunk_size}. "
                "Consider using a different split_function to reduce the size "
                "of the segments under consideration. The text that caused the "
                f"error is: \n\n{segment}",
            )

        if chunk_size + num_tokens > max_chunk_size:
            chunks.append(chunk_text + chunk_separator.strip())
            chunk_text = ""
            chunk_size = 0

        # NOTE(robinson) - To avoid the separator appearing at the beginning of the string
        if chunk_size > 0:
            chunk_text += chunk_separator
        chunk_text += segment
        chunk_size += num_tokens

        if i == (num_splits - 1) and len(chunk_text) > 0:
            chunks.append(chunk_text)

    return chunks
