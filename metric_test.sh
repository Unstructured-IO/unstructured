RUNTIME_FILE="scripts/performance/partition-speed-test/partition-runtime.txt"
REGRESSION_THRESHOLD="1.2"

# First run: no previous file exists yet
if [[ -f "$RUNTIME_FILE" ]]; then
  previous_duration=$(cat "$RUNTIME_FILE")
  # Replace 45 with the actual total from step 4b above
  current_duration=45
  threshold=$(printf "%.0f" $(echo "$previous_duration * $REGRESSION_THRESHOLD" | bc -l))
  echo "Previous: ${previous_duration}s  Current: ${current_duration}s  Threshold: ${threshold}s"
  if [ "$current_duration" -gt "$threshold" ]; then
    echo "REGRESSION DETECTED"
  else
    echo "PASS"
  fi
else
  echo "No previous runtime found - this would be saved as the baseline."
fi
