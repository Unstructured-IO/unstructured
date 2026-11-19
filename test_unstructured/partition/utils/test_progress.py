from unittest import mock

from unstructured.partition.utils import progress
from unstructured.partition.utils.progress import (
    STAGE_OCR,
    STAGE_TEXT,
    PartitionProgress,
    progress_requested,
    report_page_progress,
)


def test_progress_requested_is_false_by_default():
    assert progress_requested(None, False) is False


def test_progress_requested_with_callback_or_bar():
    assert progress_requested(lambda event: None, False) is True
    assert progress_requested(None, True) is True


def test_report_page_progress_yields_none_when_nothing_is_requested():
    with report_page_progress(STAGE_TEXT, 3) as reporter:
        assert reporter is None


def test_callback_receives_one_event_per_page():
    events: list[PartitionProgress] = []

    with report_page_progress(STAGE_TEXT, 3, progress_callback=events.append) as reporter:
        assert reporter is not None
        for _ in range(3):
            reporter.page_done()

    assert events == [
        PartitionProgress(stage=STAGE_TEXT, pages_done=1, total_pages=3),
        PartitionProgress(stage=STAGE_TEXT, pages_done=2, total_pages=3),
        PartitionProgress(stage=STAGE_TEXT, pages_done=3, total_pages=3),
    ]


def test_callback_total_pages_may_be_unknown():
    events: list[PartitionProgress] = []

    with report_page_progress(STAGE_OCR, None, progress_callback=events.append) as reporter:
        reporter.page_done()

    assert events == [PartitionProgress(stage=STAGE_OCR, pages_done=1, total_pages=None)]


def test_show_progress_draws_and_closes_a_tqdm_bar():
    bar = mock.MagicMock()
    with mock.patch("tqdm.auto.tqdm", return_value=bar) as tqdm_cls:
        with report_page_progress(STAGE_OCR, 2, show_progress=True) as reporter:
            reporter.page_done()
            reporter.page_done()

    tqdm_cls.assert_called_once_with(
        total=2, desc=f"partition {STAGE_OCR}", unit="page", leave=False
    )
    assert bar.update.call_count == 2
    bar.close.assert_called_once_with()


def test_bar_is_closed_when_the_loop_raises():
    bar = mock.MagicMock()
    with mock.patch("tqdm.auto.tqdm", return_value=bar):
        try:
            with report_page_progress(STAGE_TEXT, 2, show_progress=True) as reporter:
                reporter.page_done()
                raise RuntimeError("boom")
        except RuntimeError:
            pass

    bar.close.assert_called_once_with()


def test_no_bar_without_show_progress():
    with mock.patch("tqdm.auto.tqdm") as tqdm_cls:
        with report_page_progress(STAGE_TEXT, 2, progress_callback=lambda e: None) as reporter:
            reporter.page_done()

    tqdm_cls.assert_not_called()


def test_module_exports_stage_names():
    assert progress.STAGE_TEXT == "text"
    assert progress.STAGE_OCR == "ocr"
