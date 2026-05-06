"""Allow ``python -m unstructured``."""

from unstructured.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
