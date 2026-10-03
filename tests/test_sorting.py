import unittest

from mini_git.sorting import merge_sort


class TestMergeSort(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(merge_sort([5, 1, 4, 2, 3, 1]), [1, 1, 2, 3, 4, 5])

    def test_empty_and_single(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([7]), [7])

    def test_key_and_stability(self):
        data = [("bob", 1), ("alice", 2), ("bob", 3), ("alice", 4)]
        self.assertEqual(
            merge_sort(data, key=lambda x: x[0]),
            [("alice", 2), ("alice", 4), ("bob", 1), ("bob", 3)],
        )

    def test_does_not_mutate_input(self):
        src = [3, 2, 1]
        merge_sort(src)
        self.assertEqual(src, [3, 2, 1])

    def test_composite_key(self):
        data = [("b", 2), ("a", 2), ("c", 1)]
        self.assertEqual(
            merge_sort(data, key=lambda x: (x[1], x[0])),
            [("c", 1), ("a", 2), ("b", 2)],
        )

    def test_larger_input_is_ordered_permutation(self):
        # 시드 고정 LCG로 만든 값(중복 포함). 정렬 API 없이 "오름차순 + 같은 원소 구성"만 확인한다.
        values, x = [], 12345
        for _ in range(500):
            x = (x * 1103515245 + 12345) % 2147483648
            values.append(x % 100)
        result = merge_sort(values)
        self.assertEqual(len(result), len(values))
        for a, b in zip(result, result[1:]):
            self.assertLessEqual(a, b)
        for v in range(100):
            self.assertEqual(result.count(v), values.count(v))


if __name__ == "__main__":
    unittest.main()
