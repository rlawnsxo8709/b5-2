import hashlib
import unittest
from datetime import datetime, timedelta

from mini_git.errors import MiniGitError
from mini_git.repository import Repository


class Clock:
    """테스트용 시계. 값을 직접 움직여 같은 초·시간 차이를 재현한다."""

    def __init__(self):
        self.t = datetime(2026, 10, 4, 9, 0, 0)

    def __call__(self):
        return self.t


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.r = Repository(clock=self.clock)

    def test_requires_init(self):
        with self.assertRaisesRegex(MiniGitError, "not initialized"):
            self.r.commit("x")

    def test_every_operation_requires_init(self):
        r = self.r
        calls = [
            lambda: r.branch("b"),
            lambda: r.switch("b"),
            lambda: r.get("h"),
            lambda: r.log(),
            lambda: r.log_sorted("date"),
            lambda: r.path("a", "b"),
            lambda: r.ancestors("a"),
            lambda: r.search_keyword("x"),
            lambda: r.search_author("x"),
            lambda: r.branches_at("a"),
        ]
        for call in calls:
            with self.assertRaises(MiniGitError) as ctx:
                call()
            self.assertEqual(str(ctx.exception), "Repository not initialized. Use INIT <user_name>")
        self.assertFalse(r.initialized)

    def test_init_sets_main_head_user(self):
        self.r.init("Alice")
        self.assertEqual((self.r.current_branch, self.r.user, self.r.head_commit), ("main", "Alice", None))
        self.assertTrue(self.r.initialized)
        with self.assertRaisesRegex(MiniGitError, "already initialized"):
            self.r.init("Bob")

    def test_init_rejects_blank_user(self):
        with self.assertRaisesRegex(MiniGitError, "Invalid args"):
            self.r.init("  ")
        self.assertFalse(self.r.initialized)

    def test_branch_switch_commit_flow(self):
        r = self.r
        r.init("Alice")
        c1 = r.commit("Initial commit")
        r.branch("feature")
        r.switch("feature")
        c2 = r.commit("Add login feature")
        r.switch("main")
        c3 = r.commit("Add payment feature")
        self.assertEqual(c2.parents, (c1.hash,))
        self.assertEqual(c3.parents, (c1.hash,))
        self.assertEqual(r.path(c2.hash, c3.hash), [c2.hash, c1.hash, c3.hash])
        self.assertEqual([c.hash for c in r.ancestors(c2.hash)], [c1.hash])
        self.assertEqual(r.branches_at(c2.hash), ["feature"])

    def test_commit_moves_only_current_branch(self):
        r = self.r
        r.init("Alice")
        c1 = r.commit("first")
        r.branch("feature")
        c2 = r.commit("second")  # main만 전진한다
        self.assertEqual(r.head_commit, c2.hash)
        self.assertEqual(r.branches_at(c1.hash), ["feature"])
        self.assertEqual(r.branches_at(c2.hash), ["main"])
        r.switch("feature")
        self.assertEqual(r.head_commit, c1.hash)

    def test_errors(self):
        r = self.r
        r.init("A")
        r.commit("x")
        with self.assertRaisesRegex(MiniGitError, "Unknown branch: nope"):
            r.switch("nope")
        with self.assertRaisesRegex(MiniGitError, "Branch already exists: main"):
            r.branch("main")
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: zzz"):
            r.get("zzz")
        with self.assertRaisesRegex(MiniGitError, "Invalid args"):
            r.commit("   ")

    def test_path_and_ancestors_reject_unknown_commit(self):
        r = self.r
        r.init("A")
        c = r.commit("x")
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: zzz"):
            r.path(c.hash, "zzz")
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: zzz"):
            r.ancestors("zzz")

    def test_hash_unique_fixed_length_even_with_collisions(self):
        calls = []

        def colliding(seed):
            calls.append(seed)
            if len(calls) <= 2:
                return "aaaaaaa"  # 두 번째 커밋의 첫 해시가 충돌
            return hashlib.sha1(seed.encode()).hexdigest()[:7]

        r = Repository(clock=self.clock, hash_func=colliding)
        r.init("A")
        h1 = r.commit("one").hash
        h2 = r.commit("one").hash
        self.assertNotEqual(h1, h2)
        self.assertEqual((len(h1), len(h2)), (7, 7))
        self.assertEqual(len(calls), 3)  # salt를 바꿔 1회 재해시

    def test_same_second_commits_sorted_by_seq(self):
        r = self.r
        r.init("Bob")
        a = r.commit("first")
        b = r.commit("second")
        self.assertEqual([c.hash for c in r.log_sorted("date")], [a.hash, b.hash])

    def test_log_sorted_date_and_invalid_key(self):
        r = self.r
        r.init("Bob")
        a = r.commit("a")
        self.clock.t += timedelta(minutes=5)
        b = r.commit("b")
        self.assertEqual([c.hash for c in r.log_sorted("date")], [a.hash, b.hash])
        with self.assertRaisesRegex(MiniGitError, "Invalid args"):
            r.log_sorted("size")

    def test_log_sorted_by_date_uses_timestamp_not_creation_order(self):
        r = self.r
        r.init("Bob")
        late = r.commit("late")
        self.clock.t -= timedelta(hours=1)  # 시계가 뒤로 가도 날짜순은 timestamp를 따른다
        early = r.commit("early")
        self.assertEqual([c.hash for c in r.log_sorted("date")], [early.hash, late.hash])
        self.assertEqual([c.hash for c in r.log()], [late.hash, early.hash])

    def test_log_sorted_by_author_ties_by_seq(self):
        r = self.r
        r.init("Bob")
        b1 = r.commit("b1")
        r.user = "Alice"  # INIT은 1회뿐이라 작성자를 섞으려면 속성을 직접 바꾼다
        a1 = r.commit("a1")
        r.user = "Bob"
        b2 = r.commit("b2")
        self.assertEqual([c.hash for c in r.log_sorted("author")], [a1.hash, b1.hash, b2.hash])

    def test_log_is_parent_first_across_branches(self):
        r = self.r
        r.init("A")
        c1 = r.commit("c1")
        r.branch("f")
        r.switch("f")
        c2 = r.commit("c2")
        r.switch("main")
        c3 = r.commit("c3")
        r.switch("f")
        c4 = r.commit("c4")
        order = [c.hash for c in r.log()]
        self.assertEqual(order, [c1.hash, c2.hash, c3.hash, c4.hash])
        for c in (c2, c3, c4):
            for p in c.parents:
                self.assertLess(order.index(p), order.index(c.hash))

    def test_search_uses_index(self):
        r = self.r
        r.init("Alice")
        a = r.commit("Add login feature")
        r.user = "Bob"
        b = r.commit("Fix LOGIN bug")
        self.assertEqual([c.hash for c in r.search_keyword("login")], [a.hash, b.hash])
        self.assertEqual([c.hash for c in r.search_keyword("add login")], [a.hash])
        self.assertEqual([c.hash for c in r.search_author("Bob")], [b.hash])
        self.assertEqual(r.search_author("Nobody"), [])

    def test_branch_before_first_commit_creates_disconnected_root(self):
        r = self.r
        r.init("A")
        r.branch("orphan")
        a = r.commit("on main")
        r.switch("orphan")
        b = r.commit("on orphan")
        self.assertEqual(b.parents, ())
        self.assertIsNone(r.path(a.hash, b.hash))

    def test_path_to_self(self):
        r = self.r
        r.init("A")
        c = r.commit("x")
        self.assertEqual(r.path(c.hash, c.hash), [c.hash])


if __name__ == "__main__":
    unittest.main()
