from typing import IO, Dict, List, Any, Optional
import tempfile
from whisper import load_model
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    AudioSegment
)
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)


def transcribe(
    audio_file: str, 
    model_name: str,
    temperature: float,
    device: str = "cpu",
    verbose: bool = False,
    ) -> Dict[str, Any]:
    """
    Transcribe an audio file using a speech-to-text model.

    Args:
        audio_file: Path to the audio file to transcribe.
        model_name: Name of the model to use for transcription.
        temperature: Temperature value for Large Language Model to add randomness (0 means minimal randomness)
        device: The device to use for inference (e.g., "cpu" or "cuda"). Defaults to 'cpu'
        verbose: Print out processing statements. Defaults to False

    Returns:
        A dictionary representing the transcript, including the segments, the language code.
    """
    model = load_model(model_name, device)
    result = model.transcribe(audio_file, verbose=verbose, temperature=temperature)

    language_code = result["language"]
    return {
        "segments": result["segments"],
        "language_code": language_code,
    }


def process_segment(
    segment: Dict,
    metadata: ElementMetadata,
    keys_to_remove: List[str] = ['id', 'temperature']
) -> List[Element]:
    """
    Process individual AudioSegments from OpenAI-Whisper Into An Audio-Segment Unstructured Eleemnt

    Args:
        segment: Dictionary with all the values outputted from OpenAI-Whisper transcribe method.
        metadata: File level metadata that will be given to all elements
        keys_to_remove: Values from OpenAI-Whisper that we don't want in the Metadata

    Returns:
        An Unstructured AudioSegment Element
    """
    text = segment.pop("text")
    existing_metadata = ElementMetadata.from_dict(metadata.to_dict())
    segment_metadata = {key: value for key, value in segment.items() if key not in keys_to_remove}
    segment_metadata = ElementMetadata.from_dict(segment_metadata)
    metadata = existing_metadata.merge(segment_metadata)
    audio_element = AudioSegment(text=text, metadata=metadata)
    return audio_element
    

def partition_audio(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,  ##whatever soundfile accepts
    model_name: Optional[str] = "large",
    device: Optional[str] = "cpu",
    temperature: Optional[float] = 0.0
) -> List[Element]:
    """
    Partition Function for Audio Files

    Args:
        filename: Name of Local File to Process
        file: File Bytes In a Format that OpenAI-Whisper can process.
        model_name: What Whisper Model to use. Defaults to "large". Options are: ['tiny', 'base', 'small', 'medium', 'large'] 
        device: Pytorch device to use, "cpu" or "cuda". Defaults to "cpu" but highly recommend using "cuda" if you have a GPU configured.
        temperature: Temperature value for Large Language Model to add randomness (0 means minimal randomness)

    Returns:
        A List of Unstructured AudioSegment Elements
    """
    exactly_one(filename=filename, file=file)
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
    elif file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            filename = tmp.name
        last_modification_date = get_last_modified_date_from_file(file)
    transcript= transcribe(filename, model_name=model_name, device=device, temperature=temperature, verbose=True)
    language_code = transcript['language_code']
    metadata = ElementMetadata(filename=filename, last_modified=last_modification_date, language_code=language_code)
    segments = transcript['segments']
    elements: List[Element] = [process_segment(segment, metadata) for segment in segments]
    return elements