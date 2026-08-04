import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from unstructured.partition.utils.constants import OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT


@pytest.fixture()
def isolated_global_working_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Point `GLOBAL_WORKING_DIR` at a directory private to the requesting test.

    Any test that exercises `GLOBAL_WORKING_DIR_ENABLED` needs this. The default working dir is
    keyed on `os.getpgid(0)` (see `get_tempdir()`), a process *group*, so every pytest-xdist worker
    resolves the same path; and enabling the feature assigns the process-global `tempfile.tempdir`
    as a side effect of reading `GLOBAL_WORKING_PROCESS_DIR`. Exercising the feature against the
    default therefore writes into a directory the whole run shares, and leaves this worker putting
    every later temp file there. Redirecting the working dir keeps that shared path untouched, and
    `tempfile.tempdir` is restored on the way out.
    """
    from unstructured.partition.utils.config import get_tempdir

    saved_tempdir = tempfile.tempdir
    monkeypatch.setenv("GLOBAL_WORKING_DIR", str(tmp_path))
    # -- an explicit process dir would override the redirect; drop it for the duration --
    monkeypatch.delenv("GLOBAL_WORKING_PROCESS_DIR", raising=False)
    get_tempdir.cache_clear()
    try:
        yield tmp_path
    finally:
        tempfile.tempdir = saved_tempdir
        get_tempdir.cache_clear()


@pytest.fixture
def mock_ocr_get_instance(mocker):
    """Fixture that mocks OCRAgent.get_instance to prevent real OCR agent instantiation."""

    def mock_get_instance(ocr_agent_module, language):
        if ocr_agent_module in (OCR_AGENT_TESSERACT, OCR_AGENT_PADDLE):
            return mocker.MagicMock()
        else:
            raise ValueError(f"Unknown OCR agent: {ocr_agent_module}")

    from unstructured.partition.pdf_image.ocr import OCRAgent

    return mocker.patch.object(OCRAgent, "get_instance", side_effect=mock_get_instance)
