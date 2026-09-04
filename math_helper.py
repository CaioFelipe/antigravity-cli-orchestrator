def factorial(n: int) -> int:
    """Calcula o fatorial de n.

    Args:
        n: Numero inteiro nao negativo.

    Returns:
        O fatorial de n (n!).

    Raises:
        ValueError: Se n for negativo.
    """
    if n < 0:
        raise ValueError("n deve ser um numero inteiro nao negativo")
    resultado = 1
    for i in range(2, n + 1):
        resultado *= i
    return resultado


def is_prime(n: int) -> bool:
    """Verifica se um numero e primo.

    Args:
        n: Numero inteiro a ser verificado.

    Returns:
        True se n for primo, False caso contrario.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True
