"""Quicksort implementation with type hints and unit tests."""

from __future__ import annotations

import random
import unittest
from typing import List, TypeVar

T = TypeVar("T", int, float, str)


def quicksort(items: List[T]) -> List[T]:
    """Return a new list with items sorted in ascending order using quicksort."""
    if len(items) <= 1:
        return list(items)

    pivot = items[len(items) // 2]
    less = [x for x in items if x < pivot]
    equal = [x for x in items if x == pivot]
    greater = [x for x in items if x > pivot]

    return quicksort(less) + equal + quicksort(greater)


class QuicksortTests(unittest.TestCase):
    def test_empty_list(self) -> None:
        self.assertEqual(quicksort([]), [])

    def test_single_element(self) -> None:
        self.assertEqual(quicksort([42]), [42])

    def test_already_sorted(self) -> None:
        self.assertEqual(quicksort([1, 2, 3, 4, 5]), [1, 2, 3, 4, 5])

    def test_reverse_sorted(self) -> None:
        self.assertEqual(quicksort([5, 4, 3, 2, 1]), [1, 2, 3, 4, 5])

    def test_duplicates(self) -> None:
        self.assertEqual(quicksort([3, 1, 2, 3, 1]), [1, 1, 2, 3, 3])

    def test_negative_numbers(self) -> None:
        self.assertEqual(quicksort([-3, 1, -2, 0, 5]), [-3, -2, 0, 1, 5])

    def test_floats(self) -> None:
        self.assertEqual(quicksort([3.1, 1.4, 2.2]), [1.4, 2.2, 3.1])

    def test_strings(self) -> None:
        self.assertEqual(quicksort(["banana", "apple", "cherry"]), ["apple", "banana", "cherry"])

    def test_random_matches_builtin_sorted(self) -> None:
        data = [random.randint(-1000, 1000) for _ in range(200)]
        self.assertEqual(quicksort(data), sorted(data))

    def test_does_not_mutate_input(self) -> None:
        original = [3, 1, 2]
        result = quicksort(original)
        self.assertEqual(original, [3, 1, 2])
        self.assertEqual(result, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
