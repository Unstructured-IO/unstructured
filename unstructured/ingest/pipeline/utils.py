import hashlib


def get_ingest_doc_hash(json_as_dict: dict) -> str:
    hashed = hashlib.sha256(json_as_dict["filename"].encode()).hexdigest()[:32]
    return hashed
