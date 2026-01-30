"""Diagnostic script to verify fake-bold PDF deduplication is working."""
import os
from importlib import reload

# Set environment variable BEFORE importing unstructured modules
os.environ["PDF_CHAR_DUPLICATE_THRESHOLD"] = "0"

from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils import config as partition_config

PDF_PATH = "example-docs/pdf/fake-bold-sample.pdf"

print("=" * 70)
print("FAKE-BOLD PDF DIAGNOSTIC")
print("=" * 70)

# Extract without deduplication
print(f"\n1. WITHOUT deduplication (threshold=0):")
print("-" * 50)

elements_no_dedup = partition_pdf(filename=PDF_PATH, strategy="fast")
text_no_dedup = " ".join([el.text for el in elements_no_dedup])

print(f"Character count: {len(text_no_dedup)}")
print(f"First 200 chars:\n'{text_no_dedup[:200]}'")

# Now reload with deduplication enabled
print(f"\n2. WITH deduplication (threshold=3.0):")
print("-" * 50)

os.environ["PDF_CHAR_DUPLICATE_THRESHOLD"] = "3.0"
reload(partition_config)

elements_with_dedup = partition_pdf(filename=PDF_PATH, strategy="fast")
text_with_dedup = " ".join([el.text for el in elements_with_dedup])

print(f"Character count: {len(text_with_dedup)}")
print(f"First 200 chars:\n'{text_with_dedup[:200]}'")

# Compare
print("\n" + "=" * 70)
print("COMPARISON RESULTS:")
print("=" * 70)

diff = len(text_no_dedup) - len(text_with_dedup)
print(f"Text length WITHOUT dedup: {len(text_no_dedup)} characters")
print(f"Text length WITH dedup:    {len(text_with_dedup)} characters")
print(f"Difference:                {diff} characters removed")

if diff > 0:
    reduction_pct = (diff / len(text_no_dedup)) * 100
    print(f"Reduction:                 {reduction_pct:.1f}%")
    print("\n*** SUCCESS: Deduplication removed duplicate characters! ***")
    print("    Your PDF has fake-bold text and the fix is working.")
elif diff == 0:
    print("\n*** WARNING: No difference detected ***")
    print("    Possible reasons:")
    print("    1. The PDF doesn't have fake-bold text (uses real font weight)")
    print("    2. The deduplication threshold may need adjustment")
else:
    print("\n*** ERROR: Deduplicated text is LONGER (unexpected) ***")

# Show specific differences if any
if text_no_dedup != text_with_dedup:
    print("\n" + "-" * 50)
    print("SAMPLE TEXT COMPARISON:")
    print("-" * 50)
    print(f"WITHOUT dedup (first 100): '{text_no_dedup[:100]}'")
    print(f"WITH dedup (first 100):    '{text_with_dedup[:100]}'")
