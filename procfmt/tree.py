"""Rebuild the parent/child structure from a sequence of ProcessRecords.

Unlike parsing and formatting, this step cannot stream: a record's parent
may show up anywhere in the input, so every record has to be held until the
input ends. Memory here is proportional to the number of processes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Tuple

from .parser import ProcessRecord


@dataclass
class ProcessTree:
    # pid -> record, for the first record seen with that pid.
    records: Dict[int, ProcessRecord] = field(default_factory=dict)
    # ppid -> child pids, in input order.
    children: Dict[int, List[int]] = field(default_factory=dict)
    # Pids that start a tree: ppid 0, or a parent that is not in the input.
    roots: List[int] = field(default_factory=list)
    # The subset of roots whose named parent (other than 0) is missing.
    orphans: List[int] = field(default_factory=list)
    # Each cycle as a tuple of pids, rotated to start at its smallest pid.
    cycles: List[Tuple[int, ...]] = field(default_factory=list)
    # Later records that reused a pid already seen; they are not in the tree.
    duplicates: List[ProcessRecord] = field(default_factory=list)

    def walk(self) -> Iterator[Tuple[int, ProcessRecord]]:
        """Yield (depth, record) depth-first from each root, parents first.

        Processes that sit in or below a cycle are not reachable from any
        root and are not yielded; `cycles` reports them instead. The walk
        is iterative so a very deep chain cannot hit the recursion limit.
        """
        for root in self.roots:
            stack = [(0, root)]
            while stack:
                depth, pid = stack.pop()
                yield depth, self.records[pid]
                for child in reversed(self.children.get(pid, ())):
                    stack.append((depth + 1, child))


def build_tree(records: Iterable[ProcessRecord]) -> ProcessTree:
    tree = ProcessTree()
    for record in records:
        if record.pid in tree.records:
            tree.duplicates.append(record)
        else:
            tree.records[record.pid] = record

    for pid, record in tree.records.items():
        if record.ppid == pid:
            # A process that is its own parent is a one-element cycle.
            continue
        if record.ppid in tree.records:
            tree.children.setdefault(record.ppid, []).append(pid)
        else:
            tree.roots.append(pid)
            if record.ppid != 0:
                tree.orphans.append(pid)

    tree.cycles = _find_cycles(tree)
    return tree


def _find_cycles(tree: ProcessTree) -> List[Tuple[int, ...]]:
    reached = {pid for _, pid in _walk_pids(tree)}
    # Every unreached process has a parent that is also unreached and present
    # in the input (otherwise it would have been made a root), so following
    # ppid links from one of them can only end by revisiting a pid.
    seen = set(reached)
    cycles: List[Tuple[int, ...]] = []
    for start in tree.records:
        if start in seen:
            continue
        position: Dict[int, int] = {}
        path: List[int] = []
        current = start
        while current not in seen:
            seen.add(current)
            position[current] = len(path)
            path.append(current)
            current = tree.records[current].ppid
        if current in position:
            cycle = path[position[current]:]
            lowest = cycle.index(min(cycle))
            cycles.append(tuple(cycle[lowest:] + cycle[:lowest]))
    return cycles


def _walk_pids(tree: ProcessTree) -> Iterator[Tuple[int, int]]:
    for root in tree.roots:
        stack = [(0, root)]
        while stack:
            depth, pid = stack.pop()
            yield depth, pid
            for child in tree.children.get(pid, ()):
                stack.append((depth + 1, child))
