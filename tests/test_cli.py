import io
import pathlib
import re
import subprocess
import sys
import unittest
from datetime import datetime

from mini_git.cli import execute, repl
from mini_git.repository import Repository

ROOT = pathlib.Path(__file__).resolve().parents[1]
HASH = re.compile(r"\[(\w+) ([0-9a-f]{7})\]")
NOT_INIT = "Repository not initialized. Use INIT <user_name>"


def fixed_clock():
    return datetime(2026, 10, 4, 9, 0, 0)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.r = Repository()

    def commit(self, msg, repo=None):
        """commit 명령을 실행하고 출력에서 새 커밋 해시를 꺼낸다."""
        out = execute(repo or self.r, f'commit "{msg}"')
        return HASH.match(out).group(2)

    def test_mission_flow(self):
        r = self.r
        self.assertEqual(
            execute(r, 'INIT "Alice"'),
            "Initialized repository.\nCurrent branch: main\nCurrent user: Alice",
        )
        c1 = self.commit("Initial commit")
        self.assertEqual(execute(r, "branch feature"), "Created branch: feature")
        self.assertEqual(execute(r, "Switch feature"), "Switched to branch: feature")
        c2 = self.commit("Add login feature")
        execute(r, "switch main")
        c3 = self.commit("Add payment feature")
        log = execute(r, "log")
        self.assertLess(log.index(c1), log.index(c2))
        self.assertLess(log.index(c1), log.index(c3))
        self.assertIn("HEAD -> main", log)
        self.assertEqual(execute(r, f"path {c2} {c3}"), f"Path: {c2} -> {c1} -> {c3}")
        self.assertEqual(execute(r, "search login"), f"Found 1 commit(s):\n- {c2}: Add login feature")
        self.assertEqual(execute(r, 'search "LOGIN"'), f"Found 1 commit(s):\n- {c2}: Add login feature")
        self.assertIn(f"- {c1}: Initial commit", execute(r, f"ancestors {c3}"))

    def test_author_search_and_sort(self):
        r = self.r
        execute(r, "init Alice")
        a = self.commit("a work")
        r.user = "Bob"
        b = self.commit("b work")
        r.user = "Alice Kim"
        k = self.commit("k work")
        self.assertEqual(execute(r, 'search --author="Alice Kim"'), f"Found 1 commit(s):\n- {k}: k work")
        out = execute(r, "log --sort-by=author")
        self.assertLess(out.index(a), out.index(k))
        self.assertLess(out.index(k), out.index(b))

    def test_errors(self):
        r = self.r
        self.assertEqual(execute(r, "commit x"), NOT_INIT)
        execute(r, "init A")
        self.assertEqual(execute(r, "hello"), "Unknown command: hello")
        self.assertEqual(execute(r, "switch nope"), "Unknown branch: nope")
        self.assertEqual(execute(r, "ancestors zzz"), "Unknown commit: zzz")
        self.assertEqual(execute(r, "path onlyone"), "Invalid args")
        self.assertEqual(execute(r, 'commit "unterminated'), "Invalid args")
        self.assertEqual(execute(r, "log --sort-by=size"), "Invalid args")
        self.assertEqual(execute(r, "log"), "No commits yet")

    def test_same_commit_path(self):
        execute(self.r, "init A")
        c = self.commit("x")
        self.assertEqual(execute(self.r, f"path {c} {c}"), f"Path: {c}")

    def test_no_path_between_disconnected_roots(self):
        r = self.r
        execute(r, "init A")
        execute(r, "branch orphan")  # 첫 커밋 전에 만든 브랜치는 새 루트가 된다
        a = self.commit("on main")
        execute(r, "switch orphan")
        b = self.commit("on orphan")
        self.assertEqual(execute(r, f"path {a} {b}"), "No path")

    def test_quoted_arguments_are_single_arguments(self):
        r = self.r
        execute(r, 'init "Alice Kim"')
        out = execute(r, 'commit "Add login feature"')
        self.assertRegex(out, r"^\[main [0-9a-f]{7}\] Add login feature$")
        self.assertIn("(Alice Kim,", execute(r, "log"))

    def test_unquoted_extra_arguments_are_invalid(self):
        r = self.r
        self.assertEqual(execute(r, "init Alice Kim"), "Invalid args")
        execute(r, "init Alice")
        self.assertEqual(execute(r, "commit Add login"), "Invalid args")
        self.assertEqual(execute(r, "commit"), "Invalid args")
        self.assertEqual(execute(r, "search add login"), "Invalid args")
        self.assertEqual(execute(r, "branch a b"), "Invalid args")

    def test_commands_before_init_print_guidance(self):
        for line in [
            "log",
            "log --sort-by=date",
            "branch x",
            "switch x",
            "commit x",
            "path a b",
            "ancestors a",
            "search x",
            "search --author=A",
        ]:
            self.assertEqual(execute(self.r, line), NOT_INIT, line)

    def test_empty_repository_log_and_branch(self):
        r = self.r
        execute(r, "init A")
        self.assertEqual(execute(r, "log"), "No commits yet")
        self.assertEqual(execute(r, "log --sort-by=date"), "No commits yet")
        self.assertEqual(execute(r, "branch early"), "Created branch: early")

    def test_init_twice_and_switch_to_same_branch(self):
        r = self.r
        execute(r, "init A")
        self.assertEqual(execute(r, "init B"), "Repository already initialized")
        self.assertEqual(execute(r, "switch main"), "Already on branch: main")

    def test_command_name_is_case_insensitive_but_options_are_not(self):
        r = self.r
        execute(r, "init A")
        self.commit("x")
        self.assertEqual(execute(r, "Log --SORT-BY=Date"), "Invalid args")
        self.assertEqual(execute(r, "log --SORT-BY=date"), "Invalid args")
        self.assertEqual(execute(r, "log --sort-by=Date"), "Invalid args")
        self.assertNotEqual(execute(r, "log --sort-by=date"), "Invalid args")
        self.assertIn("commit ", execute(r, "LOG"))

    def test_log_format_and_branch_labels(self):
        r = self.r = Repository(clock=fixed_clock)
        execute(r, "init Alice")
        c1 = self.commit("Initial commit")
        execute(r, "branch feature")
        self.assertEqual(
            execute(r, "log"),
            f"commit {c1} (Alice, 2026-10-04 09:00:00) [HEAD -> main, feature]\n    Initial commit",
        )
        c2 = self.commit("Second")
        self.assertEqual(
            execute(r, "log"),
            f"commit {c1} (Alice, 2026-10-04 09:00:00) [feature]\n    Initial commit\n"
            f"commit {c2} (Alice, 2026-10-04 09:00:00) [HEAD -> main]\n    Second",
        )
        c3 = self.commit("Third")  # c2는 이제 어떤 브랜치도 가리키지 않는다
        self.assertIn(f"commit {c2} (Alice, 2026-10-04 09:00:00)\n    Second", execute(r, "log"))
        self.assertIn(c3, execute(r, "log --sort-by=date"))

    def test_merge_output_and_log(self):
        r = self.r
        execute(r, "init A")
        self.commit("root")
        execute(r, "branch feature")
        m = self.commit("on main")
        execute(r, "switch feature")
        f = self.commit("on feature")
        execute(r, "switch main")
        out = execute(r, "MERGE feature")
        merged = HASH.match(out)
        self.assertEqual(merged.group(1), "main")
        self.assertEqual(out, f"[main {merged.group(2)}] Merge branch 'feature' into main")
        self.assertIn(f"merge: {m} {f}", execute(r, "log"))
        self.assertEqual(execute(r, "merge feature"), "Already up to date")
        self.assertEqual(execute(r, "merge nope"), "Unknown branch: nope")
        self.assertEqual(execute(r, "merge"), "Invalid args")

    def test_merge_fast_forward_output(self):
        r = self.r
        execute(r, "init A")
        self.commit("root")
        execute(r, "branch feature")
        execute(r, "switch feature")
        f = self.commit("on feature")
        execute(r, "switch main")
        self.assertEqual(execute(r, "merge feature"), f"Fast-forward: main -> {f}")

    def test_user_command_and_author_sort(self):
        r = self.r
        self.assertEqual(execute(r, "user Alice"), NOT_INIT)
        execute(r, 'init "Bob"')
        b1 = self.commit("b1")
        self.assertEqual(execute(r, 'USER "Alice Kim"'), "Current user: Alice Kim")
        a1 = self.commit("a1")
        execute(r, "user Bob")
        b2 = self.commit("b2")
        log = execute(r, "log --sort-by=author")
        self.assertLess(log.index(a1), log.index(b1))
        self.assertLess(log.index(b1), log.index(b2))
        self.assertLess(execute(r, "log").index(b1), execute(r, "log").index(a1))
        self.assertEqual(execute(r, 'search --author="Alice Kim"'), f"Found 1 commit(s):\n- {a1}: a1")
        self.assertEqual(execute(r, "user"), "Invalid args")
        self.assertEqual(execute(r, 'user ""'), "Invalid args")

    def test_ancestors_output(self):
        r = self.r
        execute(r, "init A")
        c1 = self.commit("Initial commit")
        c2 = self.commit("Second")
        self.assertEqual(execute(r, f"ancestors {c2}"), f"Ancestors of {c2} (1):\n- {c1}: Initial commit")
        self.assertEqual(execute(r, f"ancestors {c1}"), f"No ancestors of {c1}")

    def test_search_edge_cases(self):
        r = self.r
        execute(r, "init Alice")
        self.commit("Add login")
        self.assertEqual(execute(r, "search nothing"), "No commits found")
        self.assertEqual(execute(r, "search --author=Nobody"), "No commits found")
        self.assertEqual(execute(r, "search --author=alice"), "No commits found")
        for bad in ["search", "search --author=", "search --foo", 'search " "', "search --author"]:
            self.assertEqual(execute(r, bad), "Invalid args", bad)

    def test_hashes_stay_unique_and_fixed_length_in_a_burst(self):
        r = self.r = Repository(clock=fixed_clock)  # 시각이 전부 같아도
        execute(r, "init A")
        hashes = [self.commit("same message") for _ in range(200)]
        self.assertEqual(len(set(hashes)), 200)
        self.assertTrue(all(len(h) == 7 for h in hashes))

    def test_blank_line_and_exit(self):
        self.assertEqual(execute(self.r, "   "), "")
        self.assertEqual(execute(self.r, "exit"), "Bye")
        self.assertEqual(execute(self.r, "Quit"), "Bye")
        self.assertEqual(execute(self.r, "exit now"), "Invalid args")


class InterruptingStdin:
    """준비된 줄을 돌려준 뒤, 다음 readline에서 Ctrl-C(KeyboardInterrupt)를 일으키는 가짜 stdin."""

    def __init__(self, lines):
        self.lines = list(lines)

    def readline(self):
        if self.lines:
            return self.lines.pop(0)
        raise KeyboardInterrupt


class TestRepl(unittest.TestCase):
    def run_repl(self, text):
        out = io.StringIO()
        code = repl(io.StringIO(text), out)
        return code, out.getvalue()

    def test_in_process_session_and_eof(self):
        code, out = self.run_repl('init "Alice"\n\nlog\n')
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            "mini-git> Initialized repository.\nCurrent branch: main\nCurrent user: Alice\n"
            "mini-git> mini-git> No commits yet\n"
            "mini-git> \n",
        )

    def test_exit_stops_processing(self):
        code, out = self.run_repl("exit now\nquit\nlog\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "mini-git> Invalid args\nmini-git> Bye\n")

    def run_interrupted(self, lines):
        """Ctrl-C가 REPL 밖으로 새면 테스트 러너가 통째로 중단되므로, 새는 경우를 실패로 바꾼다."""
        out = io.StringIO()
        try:
            code = repl(InterruptingStdin(lines), out)
        except KeyboardInterrupt:
            self.fail("KeyboardInterrupt가 REPL 밖으로 새어 나왔다")
        return code, out.getvalue()

    def test_ctrl_c_at_prompt_exits_cleanly(self):
        code, out = self.run_interrupted(['init "A"\n'])
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            "mini-git> Initialized repository.\nCurrent branch: main\nCurrent user: A\n"
            "mini-git> \n",
        )

    def test_ctrl_c_at_first_prompt(self):
        code, out = self.run_interrupted([])
        self.assertEqual(code, 0)
        self.assertEqual(out, "mini-git> \n")

    def test_session_and_eof(self):
        p = subprocess.run(
            [sys.executable, "main.py"],
            input='init "Alice"\n\ncommit "Initial commit"\nlog\n',
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=10,
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stderr, "")
        self.assertIn("mini-git> ", p.stdout)
        self.assertIn("Initial commit", p.stdout)

    def test_quit(self):
        p = subprocess.run(
            [sys.executable, "main.py"],
            input="QUIT\n",
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=10,
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stderr, "")
        self.assertIn("Bye", p.stdout)


if __name__ == "__main__":
    unittest.main()
