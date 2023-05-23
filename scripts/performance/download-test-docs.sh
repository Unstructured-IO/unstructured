#!/bin/bash

# Set the S3 bucket and key for the zip file
S3_BUCKET='utic-dev-tech-fixtures'
S3_DOCS_DIR="performance-test/docs"

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the folder name for decompression and benchmarking as a sibling of the script
LOCAL_DOCS_DIR="$SCRIPT_DIR/docs"

# Function to retrieve the file size
get_file_size() {
  local file=$1
  ls -nl "$file" | awk '{print $5}'
}

# Check if LOCAL_DOCS_DIR exists locally
if [ ! -d "$LOCAL_DOCS_DIR" ]; then
  echo "Local LOCAL_DOCS_DIR does not exist. Creating directory and downloading files from S3..."
  mkdir -p "$LOCAL_DOCS_DIR"
  aws s3 sync "s3://$S3_BUCKET/$S3_DOCS_DIR" "$LOCAL_DOCS_DIR"
  echo "Download complete."
else
  echo "Local LOCAL_DOCS_DIR exists. Synchronizing local documents with S3..."

  # Sync files from S3 that don't exist locally
  aws s3 sync "s3://$S3_BUCKET/$S3_DOCS_DIR" "$LOCAL_DOCS_DIR" --exclude "*" --include "*.*" --dryrun | grep "download:"

  # Iterate through local files
  for file in "$LOCAL_DOCS_DIR"/*; do
    if [ -f "$file" ]; then
      # Extract filename
      filename=$(basename "$file")
      # Check if the file exists in S3
      s3_etag=$(aws s3api head-object --bucket "$S3_BUCKET" --key "$S3_DOCS_DIR/$filename" --query 'ETag' --output text)
      if [ -n "$s3_etag" ]; then
        # Compare ETag values of local file and S3 file
        local_etag=$(md5sum "$file" | awk '{print $1}')
        # echo "Local ETag for '$filename': $local_etag"
        # echo "S3 ETag for '$filename': ${s3_etag//\"/}" # Remove double quotes from the ETag
        if [ "$local_etag" != "${s3_etag//\"/}" ]; then
          echo "Local file '$filename' is different from the one in S3. Replacing with the latest version..."
          aws s3 cp "s3://$S3_BUCKET/$S3_DOCS_DIR/$filename" "$LOCAL_DOCS_DIR/$filename"
        fi
      else
        # File doesn't exist in S3, delete it locally
        echo "Local file '$filename' doesn't exist in S3. Deleting..."
        rm "$file"
      fi
    fi
  done
  echo "Synchronization complete."
fi
