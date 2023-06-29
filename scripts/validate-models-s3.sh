#!/usr/bin/env bash

strategies=${STRATEGIES:=fast,hi_res,ocr_only}
input_dir=s3://utic-dev-tech-fixtures/partition-strategy-evaluation/pdf/lang/

function list_s3_dirs() {
  # s3 doesn't have a notion of directories, need to do some parsing to get them from a particular s3 path
  path=$1
  aws s3 ls "$path" | sed \$d | awk '{print $2}' | grep -E '/' | awk '{ print substr( $0, 1, length($0)-1 ) }'
}

function run_inference() {
  strategy=$1
  lang=$2
  input_path="$input_dir$lang"
  echo "Running inference with strategy $strategy and ocr language $lang on input dir $input_path"
  output_dir=partition-strategy-evaluation/output/json/$strategy
  echo "writing output content to local dir $output_dir"
  PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --remote-url "$input_path" \
    --structured-output-dir "$output_dir" \
    --preserve-downloads \
    --partition-strategy "$strategy" \
    --partition-ocr-languages "$lang" \
    --download-dir partition-strategy-evaluation/input/
}

function process_files_s3() {
  echo "Processing files from $input_dir"
  for strategy in ${strategies//,/ }
  do
    for lang in $(list_s3_dirs $input_dir)
    do
      run_inference "$strategy" "$lang"
    done
  done
}

function generate_txt_outputs() {
  # Generate text only outputs
  for strategy in ${strategies//,/ }
  do
    input_dir=partition-strategy-evaluation/output/json/"$strategy"/
    mkdir -p partition-strategy-evaluation/output/txt/"$strategy"
    echo "parsing text from generated jsons at $input_dir"
    files=$(find partition-strategy-evaluation/output/json/"$strategy" -type f -name "*.json")
    for file in $files
    do
      basename=$(basename "$file")
      new_filename=${basename%.json}.txt
      output_filepath=partition-strategy-evaluation/output/txt/"$strategy"/"$new_filename"
      echo "Getting text content from $file and writing it to $output_filepath"
      jq '.[].text' "$file" > "$output_filepath"
    done
  done
}

function upload_s3() {
  s3_output_dir="s3://utic-dev-tech-fixtures/partition-strategy-evaluation/output"

  json_output_dir="$s3_output_dir/json"

  echo "Uploading json files to s3"
  for strategy in ${strategies//,/ }
  do
    input_dir=partition-strategy-evaluation/output/json/$strategy/
    files=$(find "$input_dir" -type f -name "*.json")
    for file in $files
    do
      basename=$(basename "$file")
      s3_output_path="$json_output_dir/$strategy/$basename"
      echo "Uploading $file to $s3_output_path"
      aws s3 cp "$file" "$s3_output_path"
    done
  done

  txt_output_dir="$s3_output_dir/txt"

  echo "Uploading text files to s3"
  for strategy in ${strategies//,/ }
  do
    input_dir=partition-strategy-evaluation/output/txt/$strategy/
    files=$(find "$input_dir" -type f -name "*.txt")
    for file in $files
    do
      basename=$(basename "$file")
      s3_output_path="$txt_output_dir/$strategy/$basename"
      echo "Uploading $file to $s3_output_path"
      aws s3 cp "$file" "$s3_output_path"
    done
  done

}

echo "------------ Running model validation ------------"
process_files_s3
generate_txt_outputs
upload_s3
echo "------------ Model validation complete ------------"
