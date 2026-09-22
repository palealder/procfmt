# procfmt

Process trees show up as text in a lot of places: a `ps -ef` dump pasted
into a ticket, an audit log emitting `pid=... ppid=... cmd="..."` lines, a
support engineer's copy-paste from a terminal with tabs and spaces mixed
together. Every source formats the same three facts - a process's id, its
parent's id, and its command - a little differently, which makes it
annoying to diff, grep, or feed into anything else.

procfmt reads that mess and writes out one line per process in a single
canonical form:

```
pid<TAB>ppid<TAB>command
```

It does not try to lay the tree out visually (indentation, box-drawing
characters, etc.) - it normalizes the records so that something else (a
script, `awk`, a real tree renderer) can consume them predictably. Rows
that don't parse are skipped rather than aborting the whole run.

## Why streaming matters here

Process listings can be long-running exports - hours of audit-log output,
not a one-off `ps` snapshot. procfmt never reads the input into a list or
a big string; `parse_stream` and `write_stream` both work line by line off
whatever iterable you give them, so memory use stays flat whether the
input is 10 lines or 10 million.

## Usage

```
$ cat processes.txt
  PID  PPID COMMAND
    1     0 /sbin/init
  412     1 systemd-journald
 1055   412 sshd:   user@pts/0
pid=1400 ppid=1055 cmd="bash -c 'make test'"

$ python -m procfmt.cli processes.txt
1	0	/sbin/init
412	1	systemd-journald
1055	412	sshd: user@pts/0
1400	1055	bash -c 'make test'
```

It reads stdin and writes stdout by default, so it composes with pipes:

```
$ ps -eo pid,ppid,comm | python -m procfmt.cli | grep '\bsshd\b'
```

Or use it as a library:

```python
from procfmt import parse_stream, write_stream
import sys

with open("audit.log") as f:
    write_stream(parse_stream(f), sys.stdout)
```

## Supported input shapes

- `ps`-style whitespace columns: `PID PPID COMMAND...` (with or without a
  header row, which is detected and dropped)
- key=value lines containing `pid=`, `ppid=`, and one of `cmd=`, `comm=`,
  or `command=` (quoted or unquoted values)
- blank lines and `#`-prefixed comment lines are ignored

Lines that don't match either shape, or where pid/ppid aren't integers,
are silently skipped rather than raising - malformed input is exactly
what this tool exists to sit in front of.

## Status

Early skeleton. Parsing and canonical output work; tree reconstruction
(actually nesting children under parents, detecting cycles/orphans) is
not implemented yet.

No third-party dependencies - standard library only.
