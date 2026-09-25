import itertools
import unittest

from procfmt.parser import ProcessRecord, parse_line, parse_stream


class ParseColumnsTests(unittest.TestCase):
    def test_basic_three_column_line(self):
        self.assertEqual(
            parse_line("412 1 systemd-journald"),
            ProcessRecord(pid=412, ppid=1, command="systemd-journald"),
        )

    def test_ragged_whitespace_in_command_is_collapsed(self):
        self.assertEqual(
            parse_line(" 1055   412 sshd:   user@pts/0"),
            ProcessRecord(pid=1055, ppid=412, command="sshd: user@pts/0"),
        )

    def test_missing_command_column_defaults_to_empty(self):
        self.assertEqual(
            parse_line("1 0"),
            ProcessRecord(pid=1, ppid=0, command=""),
        )

    def test_single_token_line_is_not_a_record(self):
        self.assertIsNone(parse_line("1"))

    def test_non_numeric_pid_is_rejected(self):
        self.assertIsNone(parse_line("abc 0 init"))

    def test_non_numeric_ppid_is_rejected(self):
        self.assertIsNone(parse_line("1 abc init"))

    def test_negative_pid_and_ppid_are_valid_ints(self):
        # some listings use -1 as an orphan/unknown sentinel; int() accepts
        # it and downstream tree logic gets to decide what it means.
        self.assertEqual(
            parse_line("-1 -1 zombie"),
            ProcessRecord(pid=-1, ppid=-1, command="zombie"),
        )

    def test_header_row_is_skipped_case_insensitively(self):
        self.assertIsNone(parse_line("  PID  PPID COMMAND"))
        self.assertIsNone(parse_line("pid\tppid\tcommand"))

    def test_blank_and_comment_lines_are_skipped(self):
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))
        self.assertIsNone(parse_line("# a comment about the dump below"))

    def test_command_containing_pid_equals_falls_back_to_columns(self):
        # the substring "pid=" in the command briefly looks like a
        # key=value line, but the value isn't a valid int so parsing
        # should fall back to plain column parsing instead of dropping
        # the line entirely.
        self.assertEqual(
            parse_line("100 1 start --pid=file.pid"),
            ProcessRecord(pid=100, ppid=1, command="start --pid=file.pid"),
        )


class ParseKeyValueTests(unittest.TestCase):
    def test_basic_key_value_line(self):
        self.assertEqual(
            parse_line('pid=1400 ppid=1055 cmd="bash -c \'make test\'"'),
            ProcessRecord(pid=1400, ppid=1055, command="bash -c 'make test'"),
        )

    def test_comm_and_command_keys_are_also_accepted(self):
        self.assertEqual(
            parse_line("pid=2 ppid=1 comm=init"),
            ProcessRecord(pid=2, ppid=1, command="init"),
        )
        self.assertEqual(
            parse_line("pid=3 ppid=1 command=worker"),
            ProcessRecord(pid=3, ppid=1, command="worker"),
        )

    def test_missing_command_key_defaults_to_empty(self):
        self.assertEqual(
            parse_line("pid=5 ppid=1"),
            ProcessRecord(pid=5, ppid=1, command=""),
        )

    def test_quoted_value_containing_internal_equals_sign(self):
        self.assertEqual(
            parse_line('pid=9 ppid=1 cmd="FOO=bar baz"'),
            ProcessRecord(pid=9, ppid=1, command="FOO=bar baz"),
        )

    def test_key_order_does_not_matter(self):
        self.assertEqual(
            parse_line('cmd="worker" ppid=1 pid=9'),
            ProcessRecord(pid=9, ppid=1, command="worker"),
        )

    def test_non_numeric_pid_value_is_rejected(self):
        self.assertIsNone(parse_line("pid=abc ppid=1 cmd=init"))

    def test_non_numeric_ppid_value_is_rejected(self):
        self.assertIsNone(parse_line("pid=1 ppid=abc cmd=init"))

    def test_missing_ppid_key_falls_back_to_columns_and_fails(self):
        # no ppid= at all, and the line doesn't look like three
        # whitespace-separated columns either, so nothing parses.
        self.assertIsNone(parse_line("pid=1 cmd=init"))

    def test_quoted_pid_value_is_not_unwrapped_and_the_whole_line_fails(self):
        # _strip_quotes only ever runs on the command field, so a quoted
        # pid like pid="1" fails int() in the key=value path; the same
        # raw line also isn't valid ps-style columns, so the line is
        # dropped rather than silently coercing the quotes away.
        self.assertIsNone(parse_line('pid="1" ppid=0 cmd=init'))


class ParseStreamTests(unittest.TestCase):
    def test_skips_unparseable_lines_but_keeps_the_rest(self):
        lines = [
            "  PID  PPID COMMAND",
            "1 0 init",
            "not a process line",
            'pid=2 ppid=1 cmd="worker"',
            "",
        ]
        self.assertEqual(
            list(parse_stream(lines)),
            [
                ProcessRecord(pid=1, ppid=0, command="init"),
                ProcessRecord(pid=2, ppid=1, command="worker"),
            ],
        )

    def test_consumes_input_lazily(self):
        # a generator that raises once its second item is pulled proves
        # parse_stream isn't materializing the whole iterable up front.
        def lines():
            yield "1 0 init"
            yield "2 1 worker"
            raise AssertionError("parse_stream read further than requested")

        first = next(iter(parse_stream(lines())))
        self.assertEqual(first, ProcessRecord(pid=1, ppid=0, command="init"))

    def test_take_two_of_many_does_not_exhaust_an_infinite_source(self):
        def infinite_lines():
            pid = 1
            while True:
                yield f"{pid} {max(pid - 1, 0)} proc{pid}"
                pid += 1

        first_two = list(itertools.islice(parse_stream(infinite_lines()), 2))
        self.assertEqual(
            first_two,
            [
                ProcessRecord(pid=1, ppid=0, command="proc1"),
                ProcessRecord(pid=2, ppid=1, command="proc2"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
