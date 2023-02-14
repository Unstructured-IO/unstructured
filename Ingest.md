# Batch Processing Documents

Several classes are provided in the Unstructured library
to enable effecient batch processing of documents.

## The Abstractions

```mermaid
sequenceDiagram
    participant MainProcess
    participant DocReader (connector)
    participant DocProcessor
    participant StructuredDocWriter (conncector)
    MainProcess->>DocReader (connector): Initialize / Authorize
    DocReader (connector)->>MainProcess: All doc metadata (no file content)
    loop Single doc at a time (allows for multiprocessing)
    MainProcess->>DocProcessor: Raw document metadata (no file content)
    DocProcessor->>DocReader (connector): Request document
    DocReader (connector)->>DocProcessor: Single document payload
    Note over DocProcessor: Process through Unstructured
    DocProcessor->>StructuredDocWriter (conncector): Write Structured Data
    Note over StructuredDocWriter (conncector): <br /> Optionally store version info, filename, etc
    DocProcessor->>MainProcess: Structured Data (only JSON in V0)
    end
    Note over MainProcess: Optional - process structured data from all docs
```

## Sample Connector: S3

See the sample project [examples/ingest/s3-small-batch/main.py](examples/ingest/s3-small-batch/main.py), which processes all the documents under a given s3 URL with 2 parallel processes, writing the structured json output to `structured-outputs/`.

The abstractions in the above diagram are honored in this project (though ABC's are not yet written), with the exception of the StructuredDocWriter which may be added more formally at a later time.
