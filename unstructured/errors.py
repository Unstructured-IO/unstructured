class PdfMaxPagesExceededError(ValueError):
    """Error raised, when number of PDF pages exceeds max_pages limit
    and HI_RES strategy is chosen.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
