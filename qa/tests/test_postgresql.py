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
    
def test_crud_postgresql():
    banco = os.environ.get("PGDATABASE")

    if not banco:
        pytest.skip("Conexao PostgreSQL nao configurada nesta sessao.")

    assert banco == "automacao_n8n_test", "Use somente o banco de testes."

    with psycopg.connect(connect_timeout=5) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            assert cursor.fetchone()[0] == "automacao_n8n_test"

            cursor.execute("""
                CREATE TEMP TABLE qa_crud (
                    id INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL
                ) ON COMMIT DROP
            """)

            # Inserir e consultar.
            cursor.execute(
                "INSERT INTO pg_temp.qa_crud (id, nome) VALUES (%s, %s)",
                (1, "Teste inicial"),
            )
            cursor.execute(
                "SELECT nome FROM pg_temp.qa_crud WHERE id = %s",
                (1,),
            )
            assert cursor.fetchone() == ("Teste inicial",)

            # Atualizar e conferir.
            cursor.execute(
                "UPDATE pg_temp.qa_crud SET nome = %s WHERE id = %s",
                ("Teste atualizado", 1),
            )
            assert cursor.rowcount == 1

            cursor.execute(
                "SELECT nome FROM pg_temp.qa_crud WHERE id = %s",
                (1,),
            )
            assert cursor.fetchone() == ("Teste atualizado",)

            # Excluir e conferir.
            cursor.execute(
                "DELETE FROM pg_temp.qa_crud WHERE id = %s",
                (1,),
            )
            assert cursor.rowcount == 1

            cursor.execute("SELECT COUNT(*) FROM pg_temp.qa_crud")
            assert cursor.fetchone()[0] == 0