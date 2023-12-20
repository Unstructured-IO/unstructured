#!/usr/bin/env bash

# Performance profiling and visualization of code using cProfile and memray.

# Environment Variables:
#   - DOCKER_TEST: Set to true to run profiling inside a Docker container (default: false)

# Usage:
# - Run the script and choose the profiling mode: 'run' or 'view'.
# - In the 'run' mode, you can profile custom files or select existing test files.
# - In the 'view' mode, you can view previously generated profiling results.
# - The script supports time profiling with cProfile and memory profiling with memray.
# - Users can choose different visualization options such as flamegraphs, tables, trees, summaries, and statistics.
# - Test documents are (optionally) synced from an S3 bucket to a local directory before running the profiles.

# Dependencies:
# - memray package for memory profiling and visualization.
# - flameprof and snakeviz for time profiling and visualization.
# - AWS CLI for syncing files from S3 (if applicable).

# Package dependencies can be installed with `pip install -r scripts/performance/requirements.txt`

# Usage example:
# ./scripts/performance/profile.sh

# NOTE: because memray does not build wheels for ARM-Linux, this script can not run in an ARM Docker container on an M1 Mac (though emulated AMD would work).

# Validate dependencies
check_python_module() {
  if ! python3 -c "import $1" >/dev/null 2>&1; then
    echo "Error: Python module $1 is not installed. Please install required depencies with 'pip install -r scripts/performance/requirements.txt'."
    exit 1
  fi
}
validate_dependencies() {
  check_python_module memray
  check_python_module flameprof
}

# only validate in non-docker context (since we install dependencies on the fly in docker)
if [[ "$DOCKER_TEST" != "true" ]]; then
  validate_dependencies
fi

SCRIPT_DIR=$(dirname "$0")
# Convert the relative path to module notation
MODULE_PATH=${SCRIPT_DIR////.}
# Remove the leading dot if it exists
MODULE_PATH=${MODULE_PATH#.}
# Remove the leading dot if it exists again
MODULE_PATH=${MODULE_PATH#\.}

PROFILE_RESULTS_DIR="$SCRIPT_DIR/profile_results"

# Create PROFILE_RESULTS_DIR if it doesn't exist
mkdir -p "$PROFILE_RESULTS_DIR"

if [[ "$DOCKER_TEST" == "true" ]]; then
  SCRIPT_PARENT_DIR=$(dirname "$(dirname "$(realpath "$0")")")
  docker run -it --rm -v "$SCRIPT_PARENT_DIR:/home/unstructured/scripts" unstructured:dev /bin/bash -c "
  cd unstructured/
  pip install -r scripts/performance/requirements.txt
  echo \"Warming the Docker container by running a small partitioning job..\"
  python3 -c 'from unstructured.partition.auto import partition; partition(\"'""$SCRIPT_DIR/warmup_docs/warmup.pdf'\", strategy=\"hi_res\")[1]'
  ./scripts/performance/profile.sh
  "
  exit 0
fi

check_display() {
  if system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Display Type"; then
    return 0 # Display is present
  else
    return 1 # Display is not present (headless context)
  fi
}

view_profile_headless() {
  # Several of the visualization options require a graphical interface. If DISPLAY is not set, we can't use those options.

  extension=".bin"
  result_file="${result_file%.*}$extension"

  if [[ ! -f "$result_file" ]]; then
    unset result_file # Unset the result_file variable to go back to the "Select a file" view
    echo "Result file not found. Please choose a different profile type or go back."
  else
    while true; do
      read -r -p "Choose visualization type: (1) tree (2) summary (3) stats (b) back, (q) quit: " -n 1 visualization_type
      echo

      if [[ $visualization_type == "b" ]]; then
        unset result_file # Unset the result_file variable to go back to the "Select a file" view
        break
      elif [[ $visualization_type == "q" ]]; then
        exit 0
      fi

      case $visualization_type in
      "1")
        python3 -m memray tree "$result_file"
        ;;
      "2")
        python3 -m memray summary "$result_file"
        ;;
      "3")
        python3 -m memray stats "$result_file"
        ;;
      *)
        echo "Invalid visualization type. Please try again."
        ;;
      esac
    done
  fi
}

view_profile_with_head() {
  while true; do
    read -r -p "Choose profile type: (1) time (2) memory (3) speedscope (b) back, (q) quit: " -n 1 profile_type
    echo

    if [[ $profile_type == "b" ]]; then
      unset result_file # Unset the result_file variable to go back to the "Select a file" view
      break
    elif [[ $profile_type == "q" ]]; then
      exit 0
    fi

    if [[ $profile_type == "1" ]]; then
      extension=".prof"
    elif [[ $profile_type == "2" ]]; then
      extension=".bin"
    elif [[ $profile_type == "3" ]]; then
      extension=".speedscope"
    else
      echo "Invalid profile type. Please try again."
      continue
    fi

    result_file="${result_file%.*}$extension"

    if [[ ! -f "$result_file" ]]; then
      echo "Result file not found. Please choose a different profile type or go back."
      continue
    fi

    if [[ $profile_type == "3" ]]; then
      speedscope "$result_file"
    elif [[ $profile_type == "2" ]]; then
      while true; do
        read -r -p "Choose visualization type: (1) flamegraph (2) table (3) tree (4) summary (5) stats (b) back, (q) quit: " -n 1 visualization_type
        echo

        if [[ $visualization_type == "b" ]]; then
          break
        elif [[ $visualization_type == "q" ]]; then
          exit 0
        fi

        case $visualization_type in
        "1")
          rm -f "${result_file}.memray.html"
          python3 -m memray flamegraph -o "${result_file}.memray.html" "$result_file"
          open "${result_file}.memray.html"
          ;;
        "2")
          rm -f "${result_file}.table.html"
          python3 -m memray table -o "${result_file}.table.html" "$result_file"
          open "${result_file}.table.html"
          ;;
        "3")
          python3 -m memray tree "$result_file"
          ;;
        "4")
          python3 -m memray summary "$result_file"
          ;;
        "5")
          python3 -m memray stats "$result_file"
          ;;
        *)
          echo "Invalid visualization type. Please try again."
          ;;
        esac
      done
    else
      while true; do
        read -r -p "Choose visualization type: (1) flamegraph (2) snakeviz (b) back, (q) quit: " -n 1 visualization_type
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
          python3 -m flameprof "$result_file" >"$flameprof_file"
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

    break # Return to the beginning
  done
}

view_profile() {

  if [ -n "$1" ]; then
    result_file="$1"
  fi
  while true; do
    if [[ -z $result_file ]]; then
      echo "Available result files:"
      result_files=("$PROFILE_RESULTS_DIR"/*.bin)
      if [[ ${#result_files[@]} -eq 0 ]]; then
        echo "No result files found."
        return
      fi

      for ((i = 0; i < ${#result_files[@]}; i++)); do
        filename="${result_files[$i]##*/}"
        filename="${filename%.*}"
        echo "$i. $filename"
      done

      read -r -p "Enter the number corresponding to the result file you want to view (b to go back, q to quit): " selection
      if [[ $selection == "b" ]]; then
        return
      elif [[ $selection == "q" ]]; then
        exit 0
      fi

      result_file="${result_files[$selection]}"
    fi

    if check_display; then
      view_profile_with_head "$result_file"
    else
      view_profile_headless "$result_file"
    fi
  done
}

run_profile() {
  while true; do
    read -r -p "Choose an option: 1) Existing test file, (2) Custom file, (b) back, (q) quit: " -n 1 option
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

      for ((i = 0; i < ${#test_files[@]}; i++)); do
        echo "$i. ${test_files[$i]}"
      done

      read -r -p "Enter the number corresponding to the test file you want to run followed by return (b to go back, q to quit): " selection
      if [[ $selection == "b" ]]; then
        return
      elif [[ $selection == "q" ]]; then
        exit 0
      fi

      test_file="${test_files[$selection]}"
    elif [[ $option == "2" ]]; then
      read -r -p "Enter the path to the custom file: " test_file
    else
      echo "Invalid option. Please try again."
      continue
    fi

    # Delete the output files if they exist
    rm -f "$PROFILE_RESULTS_DIR/${test_file##*/}.prof"
    rm -f "$PROFILE_RESULTS_DIR/${test_file##*/}.bin"

    # Pick the strategy
    while true; do
      read -r -p "Choose a strategy: 1) auto, (2) fast, (3) hi_res, (4) ocr_only (b) back, (q) quit: " -n 1 strategy_option
      echo

      if [[ $strategy_option == "b" ]]; then
        return
      elif [[ $strategy_option == "q" ]]; then
        exit 0
      fi

      case $strategy_option in
      "1")
        strategy="auto"
        break
        ;;
      "2")
        strategy="fast"
        break
        ;;
      "3")
        strategy="hi_res"
        break
        ;;
      "4")
        strategy="ocr_only"
        break
        ;;
      *)
        echo "Invalid strategy option. Please try again."
        ;;
      esac
    done

    echo "Running time profile..."
    python3 -m cProfile -s cumulative -o "$PROFILE_RESULTS_DIR/${test_file##*/}.prof" -m "$MODULE_PATH.run_partition" "$test_file" "$strategy"
    echo "Running memory profile..."
    python3 -m memray run -o "$PROFILE_RESULTS_DIR/${test_file##*/}.bin" -m "$MODULE_PATH.run_partition" "$test_file" "$strategy"
    echo "Running py-spy for detailed run time profiling (this can take some time)..."
    py-spy record --subprocesses -i -o "$PROFILE_RESULTS_DIR/${test_file##*/}.speedscope" --format speedscope -- python3 -m "$MODULE_PATH.run_partition" "$test_file" "$strategy"
    echo "Profiling completed."
    echo "Viewing results for $test_file"
    echo "The py-spy produced speedscope profile can be viewed on https://www.speedscope.app or locally by installing via 'npm install -g speedscope'"
    result_file=$PROFILE_RESULTS_DIR/$(basename "$test_file")
    view_profile "${result_file}.bin" # Go directly to view mode
  done
}

while true; do
  if [[ -n "$1" ]]; then
    mode="$1"
  fi

  if [[ -z $result_file ]]; then
    read -r -p "Choose mode: (1) run, (2) view, (q) quit: " -n 1 mode
    echo
  fi

  if [[ $mode == "1" ]]; then
    run_profile
  elif [[ $mode == "2" ]]; then
    unset result_file # Unset the result_file variable before entering the "View" mode
    view_profile
  elif [[ $mode == "q" ]]; then
    exit 0
  else
    echo "Invalid mode. Please choose 'view', 'run', or 'quit'."
  fi
done
