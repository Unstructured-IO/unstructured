#!/bin/bash


# Script: Performance Profiling and Visualization
# Description: This script enables performance profiling and visualization of code using cProfile and memray.
# Author: Your Name
# Version: 1.0

# Usage: 
# - Run the script and choose the profiling mode: 'run' or 'view'.
# - In the 'run' mode, you can profile custom files or select existing test files.
# - In the 'view' mode, you can view previously generated profiling results.
# - The script supports time profiling with cProfile and memory profiling with memray.
# - Users can choose different visualization options such as flamegraphs, tables, trees, summaries, and statistics.
# - Test documents are synced from an S3 bucket to a local directory before running the profiles.

# Dependencies:
# - Python 3
# - memray package for memory profiling and visualization.
# - flameprof and snakeviz for time profiling and visualization.
# - AWS CLI for syncing files from S3 (if applicable).

# Package dependencies can be installed with `pip install -r requirements.txt`

# Usage example:
# ./performance_profiling.sh


SCRIPT_DIR=$(dirname "$0")

# Convert the relative path to module notation
MODULE_PATH=${SCRIPT_DIR////.}
# Remove the leading dot if it exists
MODULE_PATH=${MODULE_PATH#.}
# Remove the leading dot if it exists again
MODULE_PATH=${MODULE_PATH#\.}

PROFILE_RESULTS_DIR="$SCRIPT_DIR/profile_results"

S3_BUCKET="utic-dev-tech-fixtures"
S3_DOCS_DIR="performance-test/docs"

# Create PROFILE_RESULTS_DIR if it doesn't exist
mkdir -p "$PROFILE_RESULTS_DIR"

# Sync files from S3 to the local "docs" directory
aws s3 sync "s3://$S3_BUCKET/$S3_DOCS_DIR" "$SCRIPT_DIR/docs" --delete

view_profile() {
  if [ -n "$1" ]; then
    result_file="$1"
  fi
  echo "result_file: $result_file"

  while true; do
    if [[ -z $result_file ]]; then
      echo "Available result files:"
      result_files=("$PROFILE_RESULTS_DIR"/*.bin)
      if [[ ${#result_files[@]} -eq 0 ]]; then
        echo "No result files found."
        return
      fi

      for ((i=0; i<${#result_files[@]}; i++)); do
        filename="${result_files[$i]##*/}"
        filename="${filename%.*}"
        echo "$i. $filename"
      done

      read -p "Enter the number corresponding to the result file you want to view (b to go back, q to quit): " selection
      if [[ $selection == "b" ]]; then
        return
      elif [[ $selection == "q" ]]; then
        exit 0
      fi

      result_file="${result_files[$selection]}"
    fi

    while true; do
      echo "Result file: $result_file"
      read -p "Choose profile type: (1) time (2) memory (b) back, (q) quit: " -n 1 profile_type
      echo

      if [[ $profile_type == "b" ]]; then
        unset result_file  # Unset the result_file variable to go back to the "Select a file" view
        break
      elif [[ $profile_type == "q" ]]; then
        exit 0
      fi

      if [[ $profile_type == "1" ]]; then
        extension=".prof"
      elif [[ $profile_type == "2" ]]; then
        extension=".bin"
      else
        echo "Invalid profile type. Please try again."
        continue
      fi

      result_file="${result_file%.*}$extension"

      if [[ ! -f "$result_file" ]]; then
        echo "Result file not found. Please choose a different profile type or go back."
        continue
      fi

      if [[ $profile_type == "2" ]]; then
        while true; do
          read -p "Choose visualization type: (1) flamegraph (2) table (3) tree (4) summary (5) stats (b) back, (q) quit: " -n 1 visualization_type
          echo

          if [[ $visualization_type == "b" ]]; then
            break
          elif [[ $visualization_type == "q" ]]; then
            exit 0
          fi

          case $visualization_type in
            "1")
              rm -f "${result_file}.memray.html"
              python -m memray flamegraph -o "${result_file}.memray.html" "$result_file"
              open "${result_file}.memray.html"
              ;;
            "2")
              rm -f "${result_file}.table.html"
              python -m memray table -o "${result_file}.table.html" "$result_file"
              open "${result_file}.table.html"
              ;;
            "3")
              python -m memray tree "$result_file"
              ;;
            "4")
              python -m memray summary "$result_file"
              ;;
            "5")
              python -m memray stats "$result_file"
              ;;
            *)
              echo "Invalid visualization type. Please try again."
              ;;
          esac
        done
      else
        while true; do
          read -p "Choose visualization type: (1) flamegraph (2) snakeviz (b) back, (q) quit: " -n 1 visualization_type
          echo

          if [[ $visualization_type == "b" ]]; then
            break
          elif [[ $visualization_type == "q" ]]; then
            exit 0
          fi

          case $visualization_type in
            "1")
              flameprof_file="${result_file}.flameprof.svg"
              rm -f "$flameprof_file"
              flameprof "$result_file" > "$flameprof_file"
              open "$flameprof_file"
              ;;
            "2")
              snakeviz "$result_file"
              ;;
            *)
              echo "Invalid visualization type. Please try again."
              ;;
          esac
        done
      fi

      break  # Return to the beginning
    done
  done
}

run_profile() {
  while true; do
    read -p "Choose an option: 1) Existing test file, (2) Custom file, (b) back, (q) quit: " -n 1 option
    echo

    if [[ $option == "b" ]]; then
      return
    elif [[ $option == "q" ]]; then
      exit 0
    fi

    if [[ $option == "1" ]]; then
      echo "Available test files:"
      test_files=("$SCRIPT_DIR/docs"/*)
      if [[ ${#test_files[@]} -eq 0 ]]; then
        echo "No test files found."
        return
      fi

      for ((i=0; i<${#test_files[@]}; i++)); do
        echo "$i. ${test_files[$i]}"
      done

      read -p "Enter the number corresponding to the test file you want to run (b to go back, q to quit): " selection
      if [[ $selection == "b" ]]; then
        return
      elif [[ $selection == "q" ]]; then
        exit 0
      fi

      TEST_FILE="${test_files[$selection]}"
    elif [[ $option == "2" ]]; then
      read -p "Enter the path to the custom file: " TEST_FILE
    else
      echo "Invalid option. Please try again."
      continue
    fi

    # Delete the output files if they exist
    rm -f "$PROFILE_RESULTS_DIR/${TEST_FILE##*/}.prof"
    rm -f "$PROFILE_RESULTS_DIR/${TEST_FILE##*/}.bin"

    echo "Running time profile..."
    python3 -m cProfile -s cumulative -o "$PROFILE_RESULTS_DIR/${TEST_FILE##*/}.prof" -m "$MODULE_PATH.run-partition" "$TEST_FILE"
    echo "Running memory profile..."
    python3 -m memray run -o "$PROFILE_RESULTS_DIR/${TEST_FILE##*/}.bin" -m "$MODULE_PATH.run-partition" "$TEST_FILE"
    echo "Profiling completed."
    echo "Viewing results for $TEST_FILE"
    result_file=$PROFILE_RESULTS_DIR/$(basename "$TEST_FILE")
    view_profile "${result_file}.bin" # Go directly to view mode
  done
}

while true; do
  if [[ -n "$1" ]]; then
    mode="$1"
  fi
  
  if [[ -z $result_file ]]; then
    read -p "Choose mode: (1) run, (2) view, (q) quit: " -n 1 mode
    echo
  fi

  if [[ $mode == "1" ]]; then
    run_profile
  elif [[ $mode == "2" ]]; then
    unset result_file  # Unset the result_file variable before entering the "View" mode
    view_profile
  elif [[ $mode == "q" ]]; then
    exit 0
  else
    echo "Invalid mode. Please choose 'view', 'run', or 'quit'."
  fi
done
