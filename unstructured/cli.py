"""Command-line interface for :mod:`unstructured`."""

from __future__ import annotations

import argparse
import sys


def _cmd_doctor(argv: list[str] | None = None) -> int:
    from unstructured.doctor import build_report, evaluate_specifier, file_path_to_capability

    parser = argparse.ArgumentParser(
        prog="unstructured doctor",
        description="Print dependency and capability diagnostics for partitioning.",
    )
    parser.add_argument(
        "--for",
        dest="for_cap",
        metavar="TYPE",
        help="Check readiness for a file type or family (e.g. pdf, docx, image, audio).",
    )
    parser.add_argument(
        "--file",
        dest="file_path",
        metavar="PATH",
        help="Infer file type from PATH and check readiness for that type.",
    )
    ns = parser.parse_args(argv)

    if ns.for_cap and ns.file_path:
        print("Use either --for or --file, not both.", file=sys.stderr)
        return 2

    if ns.for_cap:
        try:
            result = evaluate_specifier(ns.for_cap)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if result.messages:
            print("\n".join(result.messages))
        if not result.ready:
            return 1
        return 0

    if ns.file_path:
        result = file_path_to_capability(ns.file_path)
        if result.messages:
            print("\n".join(result.messages))
        if not result.ready:
            return 1
        return 0

    print(build_report(), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``unstructured`` console script."""
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help"):
        parser = argparse.ArgumentParser(
            prog="unstructured",
            description="Unstructured document processing utilities.",
        )
        parser.add_argument(
            "command",
            nargs="?",
            choices=["doctor"],
            help="Subcommand to run.",
        )
        parser.print_help()
        return 0

    if argv[0] == "doctor":
        return _cmd_doctor(argv[1:])

    print(
        f"unstructured: unknown command {argv[0]!r}. Try `unstructured --help`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
