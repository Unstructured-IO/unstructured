class PdfMaxPagesExceededError(ValueError):
    """Error raised, when number of PDF pages exceeds max_pages limit
    and HI_RES strategy is chosen.
    """
