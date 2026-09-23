from bs4 import BeautifulSoup


def indent_html(html_string: str, html_parser="html.parser") -> str:
    """
    Formats / indents HTML.

    This function takes an HTML string and formats it using the specified HTML parser.
    It parses the HTML content and returns a prettified version of it.

    Args:
        html_string (str): The HTML content to be formatted.
        html_parser (str, optional): The parser to use for parsing the HTML. Defaults to 'html5lib':
            - 'html.parser': The built-in HTML parser. Use when you need just parsing
            - 'html5lib': The slowest. Use when you expect valid HTML parsed
                          the same way a browser does. It adds some extra
                          tags and attributes like <html>, <head>, <body>
            More in docs https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser

    Returns:
        str: The formatted and indented HTML content.
    """
    soup = BeautifulSoup(html_string, html_parser)
    pretty_html = soup.prettify()
    return pretty_html
