"""Parse loosely-formatted process listing lines into structured records.

Real process listings show up in at least three shapes in practice: the
column output of `ps`, key=value audit-log lines, and hand-pasted text with
whatever whitespace someone's terminal happened to produce. This module
turns any of those, line by line, into a single ProcessRecord shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

_HEADER_RE = re.compile(r"^\s*PID\b.*\bCOMMAND\b", re.IGNORECASE)
_KV_RE = re.compile(r'(\w+)=("[^"]*"|\S+)')
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ProcessRecord:
    pid: int
    ppid: int
    command: str


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _parse_key_value(line: str) -> Optional[ProcessRecord]:
    pairs = dict(_KV_RE.findall(line))
    if "pid" not in pairs or "ppid" not in pairs:
        return None
    command = pairs.get("cmd") or pairs.get("comm") or pairs.get("command") or ""
    try:
        pid = int(pairs["pid"])
        ppid = int(pairs["ppid"])
    except ValueError:
        return None
    return ProcessRecord(pid=pid, ppid=ppid, command=_strip_quotes(command))


def _parse_columns(line: str) -> Optional[ProcessRecord]:
    # ps-style: PID, PPID, then a ragged command column that may itself
    # contain runs of extra whitespace (args padded to align a terminal).
    parts = line.split(None, 2)
    if len(parts) < 2:
        return None
    try:
        pid = int(parts[0])
        ppid = int(parts[1])
    except ValueError:
        return None
    command = _WS_RE.sub(" ", parts[2]).strip() if len(parts) == 3 else ""
    return ProcessRecord(pid=pid, ppid=ppid, command=_strip_quotes(command))


def parse_line(line: str) -> Optional[ProcessRecord]:
    """Parse a single line, or return None if it carries no process record."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if _HEADER_RE.match(stripped):
        return None
    if "pid=" in stripped:
        record = _parse_key_value(stripped)
        if record is not None:
            return record
    return _parse_columns(stripped)


def parse_stream(lines: Iterable[str]) -> Iterator[ProcessRecord]:
    """Yield one ProcessRecord per parseable line.

    `lines` is consumed lazily, so passing a file object (or any other
    line iterator) here keeps memory use bounded to a single line at a
    time, no matter how large the input is.
    """
    for line in lines:
        record = parse_line(line)
        if record is not None:
            yield record
