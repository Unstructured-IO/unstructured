
# the general channel
export SLACK_CHANNELS=C044N0YV08G
source ~/.slack-token

rm -rf slack-ingest-download

PYTHONPATH=. ./unstructured/ingest/main.py \
        --slack-channels "${SLACK_CHANNELS}" \
        --slack-token "${SLACK_TOKEN}" \
        --download-dir slack-ingest-download \
        --structured-output-dir slack-ingest-output \
        --start-date 2023-03-01 \
        --end-date 2023-04-08T12:00:00-08:00 \
	--reprocess \
	--preserve-downloads
