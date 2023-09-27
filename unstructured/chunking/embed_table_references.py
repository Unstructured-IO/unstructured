import re
from typing import List

def embed_table_references_in_text(elements: List['Element']) -> List[Element]:
    """
    Searches for table references in the given list of elements and embeds the corresponding 
    table's HTML content directly into the text where the reference occurs. This function also 
    ensures that in case of consecutive tables, the naming does not mistakenly assign the name 
    of the second table to the first one.
    
    Parameters
    ----------
    elements
        A list of elements, where each element contains textual content and metadata indicating 
        its category (e.g., "Table"). Each element should have properties like 'text', 'category', 
        and 'metadata' which may contain a 'text_as_html' representing the table content.
    
    Returns
    -------
    List
        A list of elements with table references replaced by the table's HTML content.
    
    Note
    ----
    This function expects that table references follow the pattern "Table <number>" within the text.
    """

    table_dict = {}

    for idx, ele in enumerate(elements):
        if ele.category == "Table":
            preceding_text = elements[idx-1].text if idx > 0 else ""
            succeeding_text = elements[idx+1].text if idx < len(elements) - 1 else ""

            preceding_match = re.search(r"(Table\s+\d+)", preceding_text)
            succeeding_match = re.search(r"(Table\s+\d+)", succeeding_text)

            if preceding_match and succeeding_match:
                identification = preceding_match.group(1)
            elif preceding_match:
                identification = preceding_match.group(1)
            elif succeeding_match:
                identification = succeeding_match.group(1)
            else:
                identification = None

            if identification:
                table_dict[identification] = ele.metadata.text_as_html

    for ele in elements:
        for match in list(table_dict.keys()):
            pattern = re.compile(r'\b' + re.escape(match) + r'\b') # Using word boundaries to match exact table references
            if pattern.search(ele.text):
                ele.text = pattern.sub(match + " " + table_dict[match], ele.text)

    return elements
