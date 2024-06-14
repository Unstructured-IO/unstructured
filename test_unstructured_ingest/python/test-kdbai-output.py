import os
import sys
import kdbai_client as kdbai

endpoint = os.environ['KDBAI_ENDPOINT']
ftkey = os.environ['KDBAI_API_KEY']

if __name__ == "__main__":

    session = kdbai.Session(endpoint=endpoint,api_key=ftkey)
    documents = session.table("unstructured_test")

    try:
        assert len(documents.query()) == 5
    except AssertionError:
        sys.exit(f"Failed insert operation")
    print("Successful Insert operation")