import hashlib
import pytest

def generate_element_id(text: str, element_type: str) -> str:
    payload = f"{element_type}:{text.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def test_deterministic_element_id():
    id1 = generate_element_id("Introduction to System Architecture", "Title")
    id2 = generate_element_id("Introduction to System Architecture", "Title")
    assert id1 == id2

def test_distinct_element_ids():
    id1 = generate_element_id("Section 1", "Heading")
    id2 = generate_element_id("Section 2", "Heading")
    assert id1 != id2
