#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$(realpath "$0")")

if ! docker run -d -p 9000:9000 -p 9001:9001 --name minio-test quay.io/minio/minio server /data --console-address ":9001"; then
  echo "Couldn't start minio container"
  exit 1
fi

secret_key=minioadmin
access_key=minioadmin
region=us-east-2
endpoint_url=http://localhost:9000
bucket_name=utic-dev-tech-fixtures

retry_count=0
max_retries=6

function upload(){
  echo "Uploading test content to new bucket in minio"
  AWS_REGION=$region AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key \
  aws --output json --endpoint-url $endpoint_url s3api create-bucket --bucket $bucket_name | jq
  AWS_REGION=$region AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key \
  aws --endpoint-url $endpoint_url s3 cp "$SCRIPT_DIR"/wiki_movie_plots_small.csv s3://$bucket_name/
}

while [ "$retry_count" -lt "$max_retries" ]; do
    # Process the files only when the minio container is running

  if AWS_REGION=$region AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key aws --endpoint-url $endpoint_url s3 ls; then
    echo "Minio is active"
    docker ps --filter "name=minio-test"
    upload
    break
  else
    ((retry_count++))
    echo "Minio is not available. Retrying in 5 seconds... (Attempt $retry_count)"
    docker ps --filter "name=minio-test"
    sleep 5
  fi
done

if ! AWS_REGION=$region AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key aws --endpoint-url $endpoint_url s3 ls; then
  echo "Minio never started successfully"
fi
