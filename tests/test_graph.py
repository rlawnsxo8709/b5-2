import unittest

from mini_git.graph import ancestors, shortest_path, topo_order

# 그래프:  r <- a <- b      (main)
#          r <- c <- d      (feature)
#          x                (연결 없는 별도 루트)
P = {"r": (), "a": ("r",), "c": ("r",), "b": ("a",), "d": ("c",), "x": ()}
ORDER = ["r", "a", "c", "b", "d", "x"]


def parents_of(h):
    return P[h]


def neighbors(h):
    out = list(P[h])
    for k, ps in P.items():
        if h in ps:
            out.append(k)
    return out


class TestGraph(unittest.TestCase):
    def test_topo_parents_first(self):
        order = topo_order(ORDER, parents_of)
        self.assertEqual(len(order), 6)
        for child, ps in P.items():
            for p in ps:
                self.assertLess(order.index(p), order.index(child))
        self.assertEqual(order, ["r", "a", "c", "b", "d", "x"])

    def test_topo_cycle_raises(self):
        with self.assertRaises(ValueError):
            topo_order(["p", "q"], lambda h: {"p": ("q",), "q": ("p",)}[h])

    def test_shortest_path_through_root(self):
        self.assertEqual(shortest_path("b", "d", neighbors), ["b", "a", "r", "c", "d"])

    def test_same_node_and_no_path(self):
        self.assertEqual(shortest_path("a", "a", neighbors), ["a"])
        self.assertIsNone(shortest_path("a", "x", neighbors))

    def test_lexicographic_tie_break(self):
        # t가 m1, m2의 부모이고 m1, m2가 모두 s의 부모 -> s-m1-t / s-m2-t 동률 -> m1 선택
        Q = {"t": (), "m2": ("t",), "m1": ("t",), "s": ("m2", "m1")}

        def nb(h):
            out = list(Q[h])
            for k, ps in Q.items():
                if h in ps:
                    out.append(k)
            return out

        self.assertEqual(shortest_path("s", "t", nb), ["s", "m1", "t"])

    def test_ancestors(self):
        self.assertEqual(ancestors("b", parents_of), ["a", "r"])
        self.assertEqual(ancestors("r", parents_of), [])

    def test_topo_ties_follow_input_order(self):
        roots = {"z": (), "y": ()}
        self.assertEqual(topo_order(["z", "y"], lambda h: roots[h]), ["z", "y"])

    def test_topo_input_not_in_creation_order(self):
        # 자식이 입력에서 부모보다 앞에 있어도 부모가 먼저 나온다.
        chain = {"child": ("root",), "root": ()}
        self.assertEqual(topo_order(["child", "root"], lambda h: chain[h]), ["root", "child"])

    def test_ancestors_diamond_has_no_duplicates_and_orders_ties_by_hash(self):
        D = {"m": ("b", "a"), "a": ("r",), "b": ("r",), "r": ()}
        self.assertEqual(ancestors("m", lambda h: D[h]), ["a", "b", "r"])


if __name__ == "__main__":
    unittest.main()
