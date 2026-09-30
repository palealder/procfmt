import unittest

from procfmt.parser import ProcessRecord
from procfmt.tree import build_tree


def rec(pid, ppid, command=""):
    return ProcessRecord(pid=pid, ppid=ppid, command=command or f"p{pid}")


class BuildTreeTests(unittest.TestCase):
    def test_nests_children_under_parents_in_input_order(self):
        tree = build_tree([rec(1, 0), rec(3, 1), rec(2, 1), rec(4, 3)])
        self.assertEqual(tree.roots, [1])
        self.assertEqual(tree.children[1], [3, 2])
        self.assertEqual(tree.children[3], [4])
        self.assertEqual(tree.orphans, [])
        self.assertEqual(tree.cycles, [])

    def test_child_may_appear_before_its_parent(self):
        tree = build_tree([rec(4, 3), rec(3, 1), rec(1, 0)])
        self.assertEqual(tree.roots, [1])
        self.assertEqual(
            [(d, r.pid) for d, r in tree.walk()], [(0, 1), (1, 3), (2, 4)]
        )

    def test_missing_parent_makes_an_orphan_root(self):
        tree = build_tree([rec(1, 0), rec(50, 49), rec(51, 50)])
        self.assertEqual(tree.roots, [1, 50])
        self.assertEqual(tree.orphans, [50])
        self.assertEqual(
            [(d, r.pid) for d, r in tree.walk()], [(0, 1), (0, 50), (1, 51)]
        )

    def test_ppid_zero_is_a_root_but_not_an_orphan(self):
        tree = build_tree([rec(1, 0), rec(2, 0)])
        self.assertEqual(tree.roots, [1, 2])
        self.assertEqual(tree.orphans, [])

    def test_self_parent_is_a_cycle(self):
        tree = build_tree([rec(1, 0), rec(7, 7)])
        self.assertEqual(tree.cycles, [(7,)])
        self.assertEqual(tree.roots, [1])

    def test_two_process_cycle_is_reported_from_its_lowest_pid(self):
        tree = build_tree([rec(9, 4), rec(4, 9)])
        self.assertEqual(tree.cycles, [(4, 9)])
        self.assertEqual(tree.roots, [])
        self.assertEqual(list(tree.walk()), [])

    def test_process_hanging_off_a_cycle_is_not_a_cycle_member(self):
        tree = build_tree([rec(2, 3), rec(3, 2), rec(5, 3)])
        self.assertEqual(tree.cycles, [(2, 3)])
        self.assertEqual(list(tree.walk()), [])

    def test_separate_cycles_are_each_reported_once(self):
        tree = build_tree([rec(1, 2), rec(2, 1), rec(10, 11), rec(11, 12), rec(12, 10)])
        self.assertEqual(tree.cycles, [(1, 2), (10, 11, 12)])

    def test_duplicate_pid_keeps_the_first_record(self):
        first = rec(2, 1, "first")
        second = rec(2, 1, "second")
        tree = build_tree([rec(1, 0), first, second])
        self.assertEqual(tree.records[2], first)
        self.assertEqual(tree.duplicates, [second])
        self.assertEqual(tree.children[1], [2])

    def test_walk_handles_chains_deeper_than_the_recursion_limit(self):
        depth = 5000
        records = [rec(1, 0)] + [rec(n, n - 1) for n in range(2, depth + 1)]
        tree = build_tree(records)
        self.assertEqual(sum(1 for _ in tree.walk()), depth)

    def test_empty_input(self):
        tree = build_tree([])
        self.assertEqual(tree.roots, [])
        self.assertEqual(list(tree.walk()), [])


if __name__ == "__main__":
    unittest.main()
