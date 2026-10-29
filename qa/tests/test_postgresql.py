import os

import psycopg
import pytest


def test_conexao_postgresql():
    banco = os.environ.get("PGDATABASE")

    if not banco:
        pytest.skip("Conexao PostgreSQL nao configurada nesta sessao.")

    assert banco == "automacao_n8n_test", "Use somente o banco de testes."

    with psycopg.connect(connect_timeout=5) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT current_database(), 1 + 1")
            nome_banco, resultado = cursor.fetchone()

    assert nome_banco == "automacao_n8n_test"
    assert resultado == 2