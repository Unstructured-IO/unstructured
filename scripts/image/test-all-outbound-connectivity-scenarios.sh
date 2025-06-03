#!/usr/bin/env bash

# Note:
#
#  The scenarios baseline, missing-models, and analytics-online-only
#  are expected to have conversations reported by tshark
#
#  The scenarios offline and offline-and-missing-models
#  are *NOT* expected to have any conversations (or attempted conversations) reported by tshark

set -euo pipefail

# shellcheck disable=SC2015
((BASH_VERSINFO[0] >= 5)) || {
  echo "Requires bash >= 5" >&2
  exit 1
}

mkdir -p python-output
mkdir -p pcaps

start_timestamp_seconds=$(date +%s)

./test-outbound-connectivity.sh --cleanup baseline
./test-outbound-connectivity.sh --cleanup missing-models
./test-outbound-connectivity.sh --cleanup analytics-online-only
./test-outbound-connectivity.sh --cleanup offline
./test-outbound-connectivity.sh --cleanup offline-and-missing-models

set +e
found_pcap_files=$(find "pcaps" -maxdepth 1 -name "*.pcap" -type f -newermt "@$start_timestamp_seconds" 2>/dev/null | wc -l | tr -d ' ')
found_log_files=$(find "python-output" -maxdepth 1 -name "*.log" -type f -newermt "@$start_timestamp_seconds" 2>/dev/null | wc -l | tr -d ' ')
set -e
if [ "$found_pcap_files" -ne "5" ]; then
  echo "Expected to find 4 fresh pcap/ files from this test but found $found_pcap_files instead"
  exit 1
fi
if [ "$found_log_files" -ne "5" ]; then
  echo "Expected to find 4 fresh python-output .log files from this test but found $found_log_files instead"
  exit 1
fi

for scenario in baseline missing-models analytics-online-only offline offline-and-missing-models; do
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
