import unittest

from mini_git.index import InvertedIndex, tokenize


class TestIndex(unittest.TestCase):
    def setUp(self):
        self.ix = InvertedIndex()
        self.ix.add_commit("h1", "Add login feature", "Alice")
        self.ix.add_commit("h2", "Fix LOGIN bug", "Bob")
        self.ix.add_commit("h3", "Add payment feature", "Alice")

    def test_tokenize(self):
        self.assertEqual(tokenize("Add  Login login"), ["add", "login"])

    def test_keyword_case_insensitive(self):
        self.assertEqual(self.ix.search_keyword("login"), ["h1", "h2"])
        self.assertEqual(self.ix.search_keyword("LOGIN"), ["h1", "h2"])

    def test_multi_token_intersection(self):
        self.assertEqual(self.ix.search_keyword("add feature"), ["h1", "h3"])
        self.assertEqual(self.ix.search_keyword("add bug"), [])

    def test_author(self):
        self.assertEqual(self.ix.search_author("Alice"), ["h1", "h3"])
        self.assertEqual(self.ix.search_author("Nobody"), [])

    def test_unknown_and_empty_queries(self):
        self.assertEqual(self.ix.search_keyword("nothing"), [])
        self.assertEqual(self.ix.search_keyword("add nothing"), [])
        self.assertEqual(self.ix.search_keyword("   "), [])

    def test_author_is_case_sensitive_and_returns_copy(self):
        self.assertEqual(self.ix.search_author("alice"), [])
        self.ix.search_author("Alice").append("junk")
        self.assertEqual(self.ix.search_author("Alice"), ["h1", "h3"])


if __name__ == "__main__":
    unittest.main()
