import re


def validar_email(email: str) -> bool:
    """
    Valida se um endereço de e-mail possui um formato válido utilizando expressão regular.

    Parâmetros:
        email (str): A string contendo o endereço de e-mail a ser validado.

    Retorna:
        bool: True se o e-mail for válido, False caso contrário.

    Exemplos:
        >>> validar_email("usuario@exemplo.com")
        True
        >>> validar_email("usuario.nome+tag@dominio.com.br")
        True
        >>> validar_email("email_invalido@")
        False
        >>> validar_email("invalido@.com")
        False
    """
    if not isinstance(email, str):
        return False

    # Regex para validação de formato de e-mail:
    # - Parte local: letras, números, pontos, sublinhados, percentuais, hífens e mais
    # - Arroba (@)
    # - Domínio: letras e números, podendo ter subdomínios separados por ponto
    # - TLD (extensão): pelo menos 2 letras
    padrao = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"

    return bool(re.match(padrao, email.strip()))


if __name__ == "__main__":
    # Testes de demonstração
    emails_teste = [
        ("usuario@exemplo.com", True),
        ("nome.sobrenome@empresa.com.br", True),
        ("contato+tag@dominio.org", True),
        ("usuario123@sub.dominio.net", True),
        ("invalido@", False),
        ("@dominio.com", False),
        ("usuario@dominio", False),
        ("usuario@.com", False),
        ("usuario@dominio..com", False),
        ("espaços no email@dominio.com", False),
    ]

    print("Executando validação de e-mails de teste:\n")
    todos_passaram = True
    for email, esperado in emails_teste:
        resultado = validar_email(email)
        status = "PASSOU" if resultado == esperado else "FALHOU"
        if resultado != esperado:
            todos_passaram = False
        print(f"[{status}] {email!r:35} -> Obtido: {resultado} | Esperado: {esperado}")

    if todos_passaram:
        print("\nTodos os testes passaram com sucesso!")
