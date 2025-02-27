from typing import IO, Any, Optional


from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, VideoFragmentCaption, ElementMetadata
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata
import os
import pydub
from .audio import partition_audio
import tempfile
from moviepy.video.io.VideoFileClip import VideoFileClip
from google.cloud import aiplatform
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, Part
from functools import lru_cache
import json


@lru_cache
def get_video_model():
    vertex_creds = os.getenv("VERTEXAI_CREDENTIALS")
    if vertex_creds is None:
        raise ValueError("VERTEXAI_CREDENTIALS must be set")
    credentials_json = json.loads(vertex_creds)
    credentials = service_account.Credentials.from_service_account_info(credentials_json)

    aiplatform.init(
        location="us-west1",
        project=credentials_json["project_id"],
        credentials=credentials,
    )

    return GenerativeModel("gemini-1.5-flash")


def summarize_video_clip(filename: str, start_time: float, end_time: float) -> Element:
    print(f"Summarizing video clip from {start_time} to {end_time}")
    video = VideoFileClip(filename)
    cropped_video = video.subclipped(start_time, end_time)

    model = get_video_model()

    with tempfile.TemporaryDirectory() as tmpdirname:
        video_filepath = f"{tmpdirname}/output.mp4"
        cropped_video.write_videofile(video_filepath)
        with open(video_filepath, "rb") as fi:
            video_data = fi.read()

    response_text = model.generate_content(
        [
            Part.from_data(video_data, mime_type="video/mp4"),
            "Summarize what is happening in this video.",
        ]
    ).text

    return VideoFragmentCaption(
        text=response_text,
        metadata=ElementMetadata(start_time=start_time, end_time=end_time),
    )


@apply_metadata(FileType.MP3)
@add_chunking_strategy
def partition_video(
    filename: Optional[str] = None, *, file: Optional[IO[bytes]] = None, **kwargs: Any
) -> list[Element]:
    if not filename.lower().endswith(".mp4"):
        raise ValueError("NEED TO IMPLEMENT VIDEO CONVERSION TECHNIQUES")

    # CONVERT VIDEO TO START QUALITY

    video = pydub.AudioSegment.from_file(filename, format="mp4")
    with tempfile.TemporaryDirectory() as tmpdirname:
        mp3_filename = f"{tmpdirname}/output.mp3"
        video.export(mp3_filename, format="mp3")
        audio_elements = partition_audio(mp3_filename)

    min_clip_length = 5
    max_clip_length = 20
    start_time = 0

    elements = []
    for element in audio_elements:
        if element.metadata.start_time - start_time > max_clip_length:
            elements.append(summarize_video_clip(filename, start_time, element.metadata.start_time))
            start_time = element.metadata.start_time
            elements.append(element)
        elif element.metadata.end_time - start_time < min_clip_length:
            elements.append(element)
        else:
            elements.append(element)
            elements.append(summarize_video_clip(filename, start_time, element.metadata.end_time))
            start_time = element.metadata.end_time

    return elements
