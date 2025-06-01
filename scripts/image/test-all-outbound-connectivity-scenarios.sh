#!/usr/bin/env bash

set -euo pipefail

mkdir -p python-output
mkdir -p pcaps

start_timestamp_seconds=$(date +%s)

./test-outbound-connectivity.sh --cleanup baseline
./test-outbound-connectivity.sh --cleanup missing-models
./test-outbound-connectivity.sh --cleanup offline
./test-outbound-connectivity.sh --cleanup offline-and-missing-models

set +e
found_pcap_files=$(find "pcaps" -maxdepth 1 -name "*.pcap" -type f -newermt "@$start_timestamp_seconds" 2>/dev/null | wc -l | tr -d ' ')
found_log_files=$(find "python-output" -maxdepth 1 -name "*.log" -type f -newermt "@$start_timestamp_seconds" 2>/dev/null | wc -l | tr -d ' ')
set -e
if [ "$found_pcap_files" -ne "4" ]; then
  echo "Expected to find 4 fresh pcap/ files from this test but found $found_pcap_files instead"
  exit 1
fi
if [ "$found_log_files" -ne "4" ]; then
  echo "Expected to find 4 fresh python-output .log files from this test but found $found_log_files instead"
  exit 1
fi



for scenario in baseline missing-models offline offline-and-missing-models; do
  echo
  
  echo "=================================================================="
  echo "======================================== Begin Scenario: $scenario"
  echo 
  echo "   -------------------------------------------"
  echo "   tshark output for $scenario"
  echo "   -------------------------------------------"
  echo
  tshark -r pcaps/$scenario.pcap -q -z conv,ip | grep -v '===================================='

  echo
  echo "   ------------------------------------------"
  echo "   python log output for $scenario"
  echo "   ------------------------------------------"
  echo
  cat python-output/$scenario.log
done
  
