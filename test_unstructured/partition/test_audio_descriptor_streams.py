import tempfile
import wave
from io import BytesIO
from pathlib import Path

import pytest

from unstructured.partition import audio


@pytest.mark.parametrize("rolled_spool", [False, True])
@pytest.mark.parametrize("metadata_filename", [None, "recording.wav"])
def test_audio_partition_accepts_streams_with_descriptor_names(
    tmp_path, monkeypatch, mocker, rolled_spool, metadata_filename
):
    payload = BytesIO()
    with wave.open(payload, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 32)

    monkeypatch.setattr(audio.tempfile, "tempdir", str(tmp_path))
    agent = mocker.patch.object(audio.SpeechToTextAgent, "get_agent").return_value
    copied_paths = []

    def transcribe(path, *, language):
        copied_paths.append(Path(path))
        assert Path(path).suffix == ".wav"
        assert Path(path).read_bytes() == payload.getvalue()
        return []

    agent.transcribe_segments.side_effect = transcribe
    factory = tempfile.SpooledTemporaryFile if rolled_spool else tempfile.TemporaryFile
    with factory(mode="w+b", dir=tmp_path) as stream:
        stream.write(payload.getvalue())
        if rolled_spool:
            stream.rollover()
        stream.seek(0)
        if not isinstance(stream.name, int):
            pytest.skip("The platform gives temporary files path names instead of descriptors")

        assert audio.partition_audio(file=stream, metadata_filename=metadata_filename) == []
        assert not stream.closed
        assert len(copied_paths) == 1
        assert not copied_paths[0].exists()
