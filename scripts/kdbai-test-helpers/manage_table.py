import os
import click
import kdbai_client as kdbai

endpoint = os.environ['KDBAI_ENDPOINT']
ftkey = os.environ['KDBAI_API_KEY']
session = kdbai.Session(endpoint=endpoint,api_key=ftkey)

schema = {'columns': [
         {'name': 'id', 'pytype': 'str'},
         {'name': 'document', 'pytype': 'str'},
         {'name': 'metadata', 'pytype': 'dict'},
         {'name': 'embedding',
             'vectorIndex': {'dims': 384, 
                             'type': 'hnsw', 
                             'metric': 'L2', 
                             'efConstruction': 8, 
                             'M': 8}}]}

@click.command()
@click.option("--op", type=str, required=True)
def manage_table(op):
    if op == 'createTable':
        print('Creating kdbai table...')
        session.create_table("unstructured_test",schema)
    elif op == 'dropTable':
        if 'unstructured_test' in session.list():
            print('Dropping kdbai table...')
            session.table('unstructured_test').drop()


if __name__ == "__main__":
    manage_table()