class PageCountExceededError(ValueError):
    """Error raised, when number of pages exceeds pdf_hi_res_max_pages limit."""

    def __init__(self, document_pages: int, pdf_hi_res_max_pages: int):
        self.document_pages = document_pages
        self.pdf_hi_res_max_pages = pdf_hi_res_max_pages
        self.message = (
            f"Maximum number of PDF file pages exceeded - "
            f"pages={document_pages}, maximum={pdf_hi_res_max_pages}."
        )
        super().__init__(self.message)


class UnprocessableEntityError(Exception):
    """Error raised when a file is not valid."""


class DecompressedSizeExceededError(ValueError):
    """Error raised when decompressed data exceeds the maximum size limit."""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.message = (
            f"Decompressed data exceeds maximum allowed size of {max_size} bytes "
            f"({max_size / (1024 * 1024):.1f} MB)."
        )
        super().__init__(self.message)
