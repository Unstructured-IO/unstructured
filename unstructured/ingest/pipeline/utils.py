import hashlib
import json


def get_ingest_doc_hash(doc: str) -> str:
    json_as_dict = json.loads(doc)
    hashed = hashlib.sha256(json_as_dict.get("filename").encode()).hexdigest()[:32]
    return hashed
