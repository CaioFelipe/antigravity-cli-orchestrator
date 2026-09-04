"""
Módulo contendo implementação de busca binária com tipagem estática e testes unitários.
"""

from typing import Optional, Sequence, TypeVar
import unittest

# Define um tipo genérico para os elementos que suportam comparação
T = TypeVar("T")


def binary_search(arr: Sequence[T], target: T) -> Optional[int]:
    """
    Executa busca binária em uma sequência previamente ordenada.

    Args:
        arr (Sequence[T]): Sequência ordenada de elementos comparáveis.
        target (T): Elemento a ser procurado na sequência.

    Returns:
        Optional[int]: O índice do elemento na sequência se encontrado; caso contrário, None.
    """
    left: int = 0
    right: int = len(arr) - 1

    while left <= right:
        mid: int = (left + right) // 2
        mid_val: T = arr[mid]

        if mid_val == target:
            return mid
        elif mid_val < target:
            left = mid + 1
        else:
            right = mid - 1

    return None


class TestBinarySearch(unittest.TestCase):
    """Testes unitários para a função binary_search."""

    def test_found_in_middle(self) -> None:
        arr = [1, 3, 5, 7, 9, 11]
        self.assertEqual(binary_search(arr, 5), 2)
        self.assertEqual(binary_search(arr, 7), 3)

    def test_found_at_extremities(self) -> None:
        arr = [10, 20, 30, 40, 50]
        self.assertEqual(binary_search(arr, 10), 0)
        self.assertEqual(binary_search(arr, 50), 4)

    def test_not_found(self) -> None:
        arr = [2, 4, 6, 8, 10]
        self.assertIsNone(binary_search(arr, 1))
        self.assertIsNone(binary_search(arr, 5))
        self.assertIsNone(binary_search(arr, 15))

    def test_empty_list(self) -> None:
        self.assertIsNone(binary_search([], 10))

    def test_single_element_present(self) -> None:
        self.assertEqual(binary_search([42], 42), 0)

    def test_single_element_absent(self) -> None:
        self.assertIsNone(binary_search([42], 99))

    def test_string_sequence(self) -> None:
        names = ["Alice", "Bob", "Carlos", "Diana", "Eduardo"]
        self.assertEqual(binary_search(names, "Carlos"), 2)
        self.assertIsNone(binary_search(names, "Fernanda"))

    def test_duplicate_elements(self) -> None:
        arr = [1, 2, 2, 2, 3]
        idx = binary_search(arr, 2)
        self.assertIsNotNone(idx)
        self.assertEqual(arr[idx], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
