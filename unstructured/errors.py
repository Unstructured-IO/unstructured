class PageCountExceededError(ValueError):
    """Error raised, when number of pages exceeds max_pages limit."""

    def __init__(self, document_pages: int, max_pages: int):
        self.document_pages = document_pages
        self.max_pages = max_pages
        self.message = (
            f"Maximum number of PDF file pages exceeded - "
            f"pages={document_pages}, maximum={max_pages}."
        )
        super().__init__(self.message)
