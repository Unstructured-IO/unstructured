"""Opt-in progress reporting for partitioners that work page by page.

Partitioning a large PDF can take minutes, and callers had no way to tell how far along it was
(#2351). `partition_pdf()` and `partition_image()` accept two optional arguments that are off by
default:

- `progress_callback`: a callable that receives a `PartitionProgress` each time a page finishes.
- `show_progress`: when True, a `tqdm` bar is drawn on stderr for each reporting stage.

Both can be combined. A stage is one page-by-page pass over the document. The text layer pass
reports as `"text"`, the OCR pass as `"ocr"`. The `auto` and `hi_res` strategies can run both
passes for one document, so a callback may see the page count restart with a new stage.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

STAGE_TEXT = "text"
STAGE_OCR = "ocr"


@dataclass(frozen=True)
class PartitionProgress:
    """A snapshot of how far one page-by-page partitioning stage has progressed.

    Attributes
    ----------
    stage
        The pass that is reporting: `"text"` while the text layer is read with pdfminer, `"ocr"`
        while rendered pages are run through OCR.
    pages_done
        Pages finished so far in this stage, starting at 1.
    total_pages
        Pages the stage will process when that is known before it starts, otherwise None.
    """

    stage: str
    pages_done: int
    total_pages: Optional[int]


ProgressCallback = Callable[[PartitionProgress], None]


class PageProgressReporter:
    """Reports page completions of one stage to a callback and/or a tqdm bar."""

    def __init__(
        self,
        stage: str,
        total_pages: Optional[int],
        progress_callback: Optional[ProgressCallback],
        show_progress: bool,
    ):
        self.stage = stage
        self.total_pages = total_pages
        self.pages_done = 0
        self._progress_callback = progress_callback
        self._bar = None
        if show_progress:
            from tqdm.auto import tqdm

            self._bar = tqdm(total=total_pages, desc=f"partition {stage}", unit="page", leave=False)

    def page_done(self) -> None:
        """Record that one more page of this stage has finished."""
        self.pages_done += 1
        if self._bar is not None:
            self._bar.update(1)
        if self._progress_callback is not None:
            self._progress_callback(
                PartitionProgress(
                    stage=self.stage, pages_done=self.pages_done, total_pages=self.total_pages
                )
            )

    def close(self) -> None:
        """Release the progress bar, if one was drawn."""
        if self._bar is not None:
            self._bar.close()
            self._bar = None


def progress_requested(progress_callback: Optional[ProgressCallback], show_progress: bool) -> bool:
    """True when the caller asked for progress in either form."""
    return progress_callback is not None or bool(show_progress)


@contextmanager
def report_page_progress(
    stage: str,
    total_pages: Optional[int],
    progress_callback: Optional[ProgressCallback] = None,
    show_progress: bool = False,
) -> Iterator[Optional[PageProgressReporter]]:
    """Yield a reporter for one stage, or None when progress was not requested.

    Yielding None keeps the default path free of any progress work: callers write
    `if reporter: reporter.page_done()` and nothing else happens when the feature is off.
    """
    if not progress_requested(progress_callback, show_progress):
        yield None
        return
    reporter = PageProgressReporter(
        stage=stage,
        total_pages=total_pages,
        progress_callback=progress_callback,
        show_progress=show_progress,
    )
    try:
        yield reporter
    finally:
        reporter.close()
