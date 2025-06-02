#!/usr/bin/env bash
#
# test-outbound-connectivity.sh
#
# Capture every external packet an Unstructured Docker image emits while
# partition()‑ing a test PNG, *inside the same container* (works on macOS).
#
# In addition **also capture the Python workload's stdout / stderr** and save it
# under ./python-output/<scenario>.log while still streaming it to your terminal.
#
# Usage examples
#   ./test-outbound-connectivity.sh baseline
#   ./test-outbound-connectivity.sh --cleanup missing-models
#   ./test-outbound-connectivity.sh --cleanup offline
#   ./test-outbound-connectivity.sh offline-and-missing-models
#
# Outputs:
#   ./pcaps/<scenario>.pcap
#   ./python-output/<scenario>.log
# ---------------------------------------------------------------------

set -euo pipefail

######################## user‑tunable constants ########################
IMAGE="downloads.unstructured.io/unstructured-io/unstructured:e42884a"
NET="unstructured_test_net"
CAPTURE_IFACE="${CAPTURE_IFACE:-eth0}"
PCAP_DIR="$(pwd)/pcaps"
PY_LOG_DIR="$(pwd)/python-output" # where Python logs go
HF_CACHE="/home/notebook-user/.cache/huggingface"
########################################################################

# shellcheck disable=SC2015
((BASH_VERSINFO[0] >= 5)) || {
  echo "Requires bash >= 5" >&2
  exit 1
}

# Create output directories up‑front so failures don’t leave us empty‑handed
mkdir -p "$PCAP_DIR" "$PY_LOG_DIR"

# ---------- parse flags (optional --cleanup) --------------------------
CLEANUP=0
if [[ "${1:-}" == "--cleanup" ]]; then
  CLEANUP=1
  shift
fi

SCENARIO="${1:-}"
if [[ -z "$SCENARIO" ]]; then
  echo "Usage: $0 [--cleanup] {baseline|missing-models|offline|offline-and-missing-models}" >&2
  exit 1
fi

# ---------- optional pre‑run cleanup ----------------------------------
if ((CLEANUP)); then
  echo ">>> Removing leftover sut_* containers…"
  # shellcheck disable=SC2015
  docker rm -f "$(docker ps -aq --filter name='^sut_')" 2>/dev/null || true
fi

# ---------- scenario‑specific settings --------------------------------
DO_NOT_TRACK=""
HF_HUB_OFFLINE=""
REMOVE_CACHE=0
case "$SCENARIO" in
baseline) ;;
missing-models) REMOVE_CACHE=1 ;;
analytics-online-only) HF_HUB_OFFLINE=1 ;;
offline)
  DO_NOT_TRACK=true
  HF_HUB_OFFLINE=1
  ;;
offline-and-missing-models)
  DO_NOT_TRACK=true
  HF_HUB_OFFLINE=1
  REMOVE_CACHE=1
  ;;
*)
  echo "Unknown scenario: $SCENARIO"
  exit 1
  ;;
esac

docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"

# ---------- launch SUT idle -------------------------------------------
CID=$(docker run -d --rm --name "sut_${SCENARIO}" \
  --network "$NET" \
  --cap-add NET_RAW --cap-add NET_ADMIN \
  -e DO_NOT_TRACK="$DO_NOT_TRACK" \
  -e HF_HUB_OFFLINE="$HF_HUB_OFFLINE" \
  --entrypoint /bin/sh "$IMAGE" -c "sleep infinity")
echo "Container: $CID  (scenario $SCENARIO)"

# install tcpdump (Wolfi uses apk) as root
docker exec -u root "$CID" apk add --no-cache tcpdump >/dev/null

# optionally wipe HF cache
# shellcheck disable=SC2015
((REMOVE_CACHE)) && docker exec "$CID" rm -rf "$HF_CACHE" || true

# ---------- start tcpdump in background -------------------------------
FILTER='not (dst net ff02::/16 or src net ff02::/16 or ip6[6] = 58 or ether multicast)'

docker exec -u root -d "$CID" sh -c "tcpdump -U -n -i $CAPTURE_IFACE '$FILTER' -w /tmp/capture.pcap > /tmp/tcpdump.log 2>&1"

# check if tcpdump stayed alive
sleep 2
if ! docker exec "$CID" pgrep tcpdump >/dev/null; then
  echo 'tcpdump exited – showing its log:'
  docker exec "$CID" cat /tmp/tcpdump.log
  exit 1
fi

echo "tcpdump running on interface $CAPTURE_IFACE..."
# ---------- run the Python workload -----------------------------------
echo ">>> Running Python workload (capturing stdout/stderr)…"
#   ‑ The "|&" pipes *both* stdout *and* stderr into tee.
#   ‑ tee sends it to the terminal *and* writes the log file.
#   ‑ With `set -o pipefail` we still fail early if the Python process exits non‑zero.

if [[ "$HF_HUB_OFFLINE" -eq 1 && "$REMOVE_CACHE" -eq 1 ]]; then
  echo "HF_HUB_OFFLINE=1 and REMOVE_CACHE=1 : allowing python command have a non-exit 0 status and will continue the script."
  set +e
fi

docker exec -i -e PYTHONUNBUFFERED=1 "$CID" python - <<PY |& tee "${PY_LOG_DIR}/${SCENARIO}.log"
import logging
from unstructured.partition.auto import partition
from unstructured.logger import logger  # force analytics ping if not DO_NOT_TRACK
import urllib.request, time, os, sys

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_platform_api.log')
    ]
)
logging.getLogger("urllib").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)
logging.getLogger("pdfminer.pdfpage").setLevel(logging.CRITICAL)

for test_file in [
 "/app/example-docs/ideas-page.html",
 "/app/example-docs/category-level.docx",
 "/app/example-docs/fake_table.docx",
 "/app/example-docs/img/english-and-korean.png",
 "/app/example-docs/img/embedded-images-tables.jpg",
 "/app/example-docs/img/layout-parser-paper-with-table.jpg",
 "/app/example-docs/pdf/embedded-images-tables.pdf",
 "/app/example-docs/pdf/all-number-table.pdf",
 "/app/example-docs/fake-power-point.pptx",
 "/app/example-docs/stanley-cups.xlsx",
 "/app/example-docs/fake-email-multiple-attachments.msg",
]:
 print("[INFO] partitioning "+test_file)
 partition(test_file, strategy="hi_res", skip_infer_table_types=[])
## add this if you always want to force an external connection
#print("[INFO] done partitioning; hitting google…")
#urllib.request.urlopen("https://www.google.com", timeout=10).read(64)
#print("[INFO] google fetch finished")

time.sleep(1)  # ensure FIN packets captured
PY

echo "Python finished.  Log saved to ${PY_LOG_DIR}/${SCENARIO}.log"

set -e

# ---------- stop tcpdump, copy pcap, clean up -------------------------
docker exec "$CID" pkill -2 tcpdump || true
sleep 1 # let pcap flush

docker cp "$CID:/tmp/capture.pcap" "${PCAP_DIR}/${SCENARIO}.pcap"
echo "pcap saved to ${PCAP_DIR}/${SCENARIO}.pcap"

docker stop "$CID" >/dev/null
