collect_ignore_glob = []

try:
    import pytest_benchmark  # noqa: F401
except ImportError:
    collect_ignore_glob.append("test_benchmark_*.py")
