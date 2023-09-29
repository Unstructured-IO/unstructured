SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

  PYTHONPATH=. ./unstructured/ingest/main.py \
    sharepoint \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --client-cred "$SHAREPOINT_CRED" \
    --client-id "$SHAREPOINT_CLIENT_ID" \
    --site "$SHAREPOINT_SITE" \
    --path "Shared Documents" \
    --recursive \
    --embedding-api-key "$OPENAI_API_KEY" \
    --chunk-elements \
    --chunk-multipage-sections \
