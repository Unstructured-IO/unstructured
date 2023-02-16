import multiprocessing as mp
import os
from unstructured.ingest.connector.s3_connector import S3Connector, SimpleS3Config
from unstructured.ingest.doc_processor.generalized import initialize, process_document

class MainProcess:

    def __init__(self, doc_connector, doc_processor_fn, num_processes):
        # initialize the reader and writer
        self.doc_connector = doc_connector
        self.doc_processor_fn = doc_processor_fn
        self.num_processes = num_processes
        

    def initialize(self):
        """Slower initialization things: check connections, load things into memory, etc."""
        initialize()
        
    def cleanup(self):
        self.doc_connector.cleanup()

    def run(self):
        self.initialize()

        self.doc_connector.fetch_docs()

        # fetch the list of lazy downloading IngestDoc obj's
        docs = self.doc_connector.fetch_docs()

        # Debugging tip: use the below line and comment out the mp.Pool loop
        # block to remain in single process
        # self.doc_processor_fn(docs[0])

        with mp.Pool(processes=self.num_processes) as pool:
            results = pool.map(self.doc_processor_fn, docs)
        
        
        self.cleanup()

    @staticmethod
    def main():
        doc_connector = S3Connector(
            config=SimpleS3Config(
                s3_url="s3://utic-dev-tech-fixtures/small-pdf-set/",
                output_dir="structured-output",
                # set to False to use your AWS creds (not needed for this public s3 url)
                anonymous=True,
            ),
        )
        MainProcess(doc_connector=doc_connector,
                    doc_processor_fn=process_document,
                    num_processes=2).run()

if __name__ == '__main__':
    MainProcess.main()
