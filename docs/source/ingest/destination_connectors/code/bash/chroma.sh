unstructured-ingest \
    local \
    --input-path example-docs/book-war-and-peace-1225p.txt \
    --output-dir local-to-pinecone \
    --strategy fast \
    --chunk-elements \
    --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
    --num-processes 2 \
    --verbose \
    --work-dir "<directory for intermediate outputs to be saved>" \
    chroma \
    --host "localhost" \
    --port 8000 \
    --collection-name "collection_name" \
    --batch-size 80
