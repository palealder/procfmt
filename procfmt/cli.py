"""Command-line entry point: normalize messy process-listing text."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence, TextIO

from .formatter import write_stream
from .parser import parse_stream


def _open_input(path: str) -> TextIO:
    if path == "-":
        return sys.stdin
    return open(path, "r", encoding="utf-8", errors="replace")


def _open_output(path: str) -> TextIO:
    if path == "-":
        return sys.stdout
    return open(path, "w", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="procfmt",
        description="Normalize messy process-listing input into pid<TAB>ppid<TAB>command lines.",
    )
    parser.add_argument(
        "input", nargs="?", default="-", help="input file, or - for stdin (default)"
    )
    parser.add_argument(
        "-o", "--output", default="-", help="output file, or - for stdout (default)"
    )
    args = parser.parse_args(argv)

    in_stream = _open_input(args.input)
    out_stream = _open_output(args.output)
    try:
        write_stream(parse_stream(in_stream), out_stream)
    finally:
        if in_stream is not sys.stdin:
            in_stream.close()
        if out_stream is not sys.stdout:
            out_stream.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
