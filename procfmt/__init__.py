"""procfmt: normalize messy process-listing text into a canonical form."""

from .formatter import format_record, write_stream
from .parser import ProcessRecord, parse_line, parse_stream

from .tree import ProcessTree, build_tree

__version__ = "0.1.0"

__all__ = [
    "ProcessTree",
    "build_tree",
    "ProcessRecord",
    "parse_line",
    "parse_stream",
    "format_record",
    "write_stream",
    "__version__",
]
