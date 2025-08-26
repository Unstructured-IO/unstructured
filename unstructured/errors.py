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
