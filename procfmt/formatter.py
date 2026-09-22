"""Render ProcessRecord objects back out in a single canonical form."""

from __future__ import annotations

from typing import Iterable, TextIO

from .parser import ProcessRecord

FIELD_SEP = "\t"


def format_record(record: ProcessRecord) -> str:
    # Tabs and newlines in a command would break the one-line-per-record
    # contract downstream tools rely on, so they get flattened to spaces.
    command = record.command.replace("\t", " ").replace("\n", " ")
    return f"{record.pid}{FIELD_SEP}{record.ppid}{FIELD_SEP}{command}"


def write_stream(records: Iterable[ProcessRecord], out: TextIO) -> None:
    """Write each record to `out` as it arrives.

    This loops over `records` rather than collecting them into a list
    first, which is what lets a caller pipe an unbounded input through
    procfmt without holding the whole thing in memory at once.
    """
    for record in records:
        out.write(format_record(record))
        out.write("\n")
