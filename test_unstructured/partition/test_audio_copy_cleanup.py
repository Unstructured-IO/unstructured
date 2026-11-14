from io import BytesIO
from pathlib import Path

import pytest

from unstructured.file_utils.model import FileType
from unstructured.partition import audio


@pytest.mark.parametrize("failure", [OSError("read failed"), KeyboardInterrupt()])
@pytest.mark.parametrize("partial", [False, True])
def test_audio_copy_failure_removes_the_temporary_file(
    tmp_path, monkeypatch, mocker, failure, partial
):
    class FailingStream(BytesIO):
        def read(self, size=-1):
            if partial and self.tell() == 0:
                return super().read(4)
            raise failure

    monkeypatch.setattr(audio.tempfile, "tempdir", str(tmp_path))
    mocker.patch.object(audio, "detect_filetype", return_value=FileType.WAV)
    get_agent = mocker.patch.object(audio.SpeechToTextAgent, "get_agent")
    stream = FailingStream(b"RIFFaudio data")

    with pytest.raises(type(failure)) as caught:
        audio.partition_audio(file=stream, metadata_filename="recording.wav")

    assert caught.value is failure
    assert list(tmp_path.iterdir()) == []
    assert not stream.closed
    get_agent.assert_not_called()


@pytest.mark.parametrize("agent_fails", [False, True])
def test_audio_copy_is_available_to_the_agent_then_removed(
    tmp_path, monkeypatch, mocker, agent_fails
):
    monkeypatch.setattr(audio.tempfile, "tempdir", str(tmp_path))
    mocker.patch.object(audio, "detect_filetype", return_value=FileType.WAV)
    agent = mocker.patch.object(audio.SpeechToTextAgent, "get_agent").return_value
    payload = b"RIFFaudio data"

    def transcribe(path, *, language):
        assert Path(path).read_bytes() == payload
        assert language == "en"
        if agent_fails:
            raise RuntimeError("transcription failed")
        return []

    agent.transcribe_segments.side_effect = transcribe
    stream = BytesIO(payload)
    if agent_fails:
        with pytest.raises(RuntimeError, match="transcription failed"):
            audio.partition_audio(file=stream, metadata_filename="recording.wav", language="en")
    else:
        assert (
            audio.partition_audio(file=stream, metadata_filename="recording.wav", language="en")
            == []
        )

    assert list(tmp_path.iterdir()) == []
    assert not stream.closed
