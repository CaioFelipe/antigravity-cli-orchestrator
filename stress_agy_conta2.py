"""
Módulo contendo função para cálculo de hash SHA-256, suíte de testes unitários
e teste de estresse/desempenho.
"""

from typing import Union, Dict, Any
import hashlib
import time
import unittest


def gerar_hash_sha256(dados: Union[str, bytes], codificacao: str = "utf-8") -> str:
    """
    Calcula o hash criptográfico SHA-256 de uma string ou sequência de bytes.

    Args:
        dados (Union[str, bytes]): Dado a ser hasheado (string ou bytes).
        codificacao (str, opcional): Codificação de caracteres a ser usada caso seja string.
                                     Padrão é 'utf-8'.

    Returns:
        str: Representação hexadecimal do hash SHA-256 (64 caracteres).

    Raises:
        TypeError: Se 'dados' não for uma instância de str ou bytes.
    """
    if isinstance(dados, str):
        dados_bytes = dados.encode(codificacao)
    elif isinstance(dados, (bytes, bytearray)):
        dados_bytes = bytes(dados)
    else:
        raise TypeError(f"Esperado str ou bytes, mas recebido {type(dados).__name__}")

    return hashlib.sha256(dados_bytes).hexdigest()


def executar_teste_estresse(
    qtd_iteracoes: int = 50_000,
    tamanho_dados: int = 256,
) -> Dict[str, Any]:
    """
    Executa um teste de estresse calculando hashes SHA-256 em lote
    e mede o tempo de execução e taxa de operações por segundo.

    Args:
        qtd_iteracoes (int): Quantidade de operações de hash a realizar.
        tamanho_dados (int): Tamanho em bytes de cada bloco a ser hasheado.

    Returns:
        Dict[str, Any]: Estatísticas contendo total de iterações, tempo gasto e hashes/segundo.
    """
    amostra = b"x" * tamanho_dados
    inicio = time.perf_counter()

    for _ in range(qtd_iteracoes):
        _ = hashlib.sha256(amostra).hexdigest()

    fim = time.perf_counter()
    duracao = fim - inicio
    hashes_por_segundo = qtd_iteracoes / duracao if duracao > 0 else float("inf")

    return {
        "iteracoes": qtd_iteracoes,
        "tamanho_bloco_bytes": tamanho_dados,
        "tempo_total_segundos": duracao,
        "hashes_por_segundo": hashes_por_segundo,
    }


class TestSHA256(unittest.TestCase):
    """Suíte de testes unitários para a função gerar_hash_sha256."""

    def test_hash_string_vazia(self) -> None:
        esperado = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertEqual(gerar_hash_sha256(""), esperado)
        self.assertEqual(gerar_hash_sha256(b""), esperado)

    def test_hash_vetores_conhecidos(self) -> None:
        casos = [
            ("hello", "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
            ("Hello, World!", "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"),
            ("teste_sha256_antigravity", "227d3aa0e906a8b932c2352247529bbf4dfbc04e534662321e1e6e5f23c4e7a2"),
        ]
        for texto, hash_esperado in casos:
            with self.subTest(texto=texto):
                resultado_str = gerar_hash_sha256(texto)
                resultado_bytes = gerar_hash_sha256(texto.encode("utf-8"))
                self.assertEqual(resultado_str, hash_esperado)
                self.assertEqual(resultado_bytes, hash_esperado)

    def test_formato_do_hash(self) -> None:
        resultado = gerar_hash_sha256("qualquer_conteudo")
        self.assertIsInstance(resultado, str)
        self.assertEqual(len(resultado), 64)
        # Todos os caracteres devem ser hexadecimais em minúsculo
        self.assertTrue(all(c in "0123456789abcdef" for c in resultado))

    def test_determinismo(self) -> None:
        entrada = "dados_imutaveis_123"
        self.assertEqual(gerar_hash_sha256(entrada), gerar_hash_sha256(entrada))

    def test_efeito_avalanche(self) -> None:
        hash1 = gerar_hash_sha256("mensagemA")
        hash2 = gerar_hash_sha256("mensagemB")
        self.assertNotEqual(hash1, hash2)

    def test_tipo_invalido(self) -> None:
        with self.assertRaises(TypeError):
            gerar_hash_sha256(12345)  # type: ignore

        with self.assertRaises(TypeError):
            gerar_hash_sha256(None)  # type: ignore

    def test_bytearray(self) -> None:
        dados = bytearray(b"bytes_mutaveis")
        self.assertEqual(gerar_hash_sha256(dados), gerar_hash_sha256(b"bytes_mutaveis"))


if __name__ == "__main__":
    print("=" * 60)
    print("1. EXECUTANDO TESTES UNITARIOS")
    print("=" * 60)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSHA256)
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)

    if resultado.wasSuccessful():
        print("\n" + "=" * 60)
        print("2. EXECUTANDO TESTE DE ESTRESSE / DESEMPENHO")
        print("=" * 60)
        estatisticas = executar_teste_estresse(qtd_iteracoes=50_000, tamanho_dados=256)
        print(f"Iteracoes:             {estatisticas['iteracoes']:,}")
        print(f"Tamanho do bloco:      {estatisticas['tamanho_bloco_bytes']} bytes")
        print(f"Tempo total:           {estatisticas['tempo_total_segundos']:.4f} s")
        print(f"Taxa de processamento: {estatisticas['hashes_por_segundo']:,.2f} hashes/s")
        print("=" * 60)
        print("Finalizado com sucesso!")
    else:
        print("\nFalha nos testes unitarios!")
