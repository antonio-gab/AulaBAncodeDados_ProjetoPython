"""Prepara somente o banco dedicado ao laboratorio local."""
from pathlib import Path
import os
import argparse

import sys
import subprocess

RAIZ = Path(__file__).resolve().parent

try:
    import psycopg
    from dotenv import dotenv_values
except (ImportError, ModuleNotFoundError):
    if __name__ != "__main__":
        raise
    print("Instalando dependencias neste Python. Requer internet e permissao de instalacao.", flush=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(RAIZ / "requirements.txt")],
            check=True, capture_output=True, text=True,
        )
        import psycopg
        from dotenv import dotenv_values
    except (subprocess.CalledProcessError, OSError, ImportError):
        print("Nao foi possivel instalar. Confira internet, pip e permissoes. Veja roteiro.pdf para instalacao manual.")
        raise SystemExit(1)

from psycopg import sql


def preparar():
    parser = argparse.ArgumentParser(description="Prepara o laboratorio local sem pgAdmin.")
    parser.add_argument("--reset", action="store_true", help="Feche A e B antes. Restaura apenas os dados ficticios.")
    args = parser.parse_args()
    if args.reset:
        print("Feche A e B antes do reset. Somente os dados ficticios de lab_fluxo serao restaurados.", flush=True)
    for chave in tuple(os.environ):
        if chave.startswith("PG"):
            os.environ.pop(chave, None)
    config = dotenv_values(RAIZ / ".env", interpolate=False)
    parametros = dict(
        host=config.get("DB_HOST", "localhost"),
        port=int(config.get("DB_PORT", "5432")),
        dbname=config.get("DB_NAME", "transacao"),
        user=config.get("DB_USER", "postgres"),
        password=config.get("DB_PASSWORD", "ceub123456"),
        connect_timeout=5, options="", autocommit=True,
    )
    banco = parametros["dbname"]
    if not banco or banco.lower() in ("postgres", "template0", "template1"):
        print("Recusado: escolha um banco de laboratorio, nunca um banco de sistema.")
        return 1
    with psycopg.connect(**dict(parametros, dbname="postgres")) as admin:
        existe = admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (banco,)).fetchone()
        if not existe:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(banco)))
            print("Banco de laboratorio criado.")
    with psycopg.connect(**parametros) as conexao:
        existe_schema = conexao.execute("SELECT 1 FROM pg_namespace WHERE nspname='lab_fluxo'").fetchone()
        if existe_schema:
            print("Schema existente: dados preservados, sem reset automatico.")
        else:
            conexao.execute((RAIZ / "preparacao.sql").read_text(encoding="utf-8"))
        # Verifique a estrutura antes de tentar qualquer reset.
        conexao.execute("SELECT id, nome, saldo FROM lab_fluxo.conta LIMIT 0")
        conexao.execute("SELECT id, nome, ativo FROM lab_fluxo.plantao LIMIT 0")
        if args.reset:
            conexao.execute("SET lock_timeout = '3s'")
            conexao.execute((RAIZ / "reset.sql").read_text(encoding="utf-8"))
            print("Reset concluido.")
        contas = conexao.execute("SELECT id, nome, saldo FROM lab_fluxo.conta ORDER BY id").fetchall()
        plantao = conexao.execute("SELECT id, nome, ativo FROM lab_fluxo.plantao ORDER BY id").fetchall()
        print("Contas:", contas, "Total:", sum(c[2] for c in contas))
        print("Plantao:", plantao)
    print("Preparacao concluida. Abra A e B no VS Code.")
    return 0


def main():
    try:
        return preparar()
    except (ValueError, TypeError):
        print("Configuracao invalida no .env. Confira os campos e a porta numerica.")
    except psycopg.errors.InsufficientPrivilege:
        print("Sem permissao para criar banco/schema ou acessar os dados. Use seu PostgreSQL local com usuario autorizado.")
    except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn, psycopg.errors.InvalidSchemaName):
        print("Schema lab_fluxo incompleto ou incompativel. Nada sera apagado automaticamente; procure o professor.")
    except psycopg.errors.LockNotAvailable:
        print("Reset nao realizado: ha bloqueio. Termine as transacoes e feche A e B antes de tentar novamente.")
    except psycopg.OperationalError as erro:
        if erro.sqlstate in ("28P01", "28000") or "authentication" in str(erro).lower():
            print("Falha de autenticacao. Edite DB_USER/DB_PASSWORD no .env para corresponder ao servidor. Nao altere a senha do servidor.")
        else:
            print("Falha de conexao. Confira servico PostgreSQL iniciado, DB_HOST e DB_PORT no .env.")
    except psycopg.Error:
        print("PostgreSQL recusou a operacao. Confira se o banco e exclusivo do laboratorio e procure o professor.")
    except OSError:
        print("Nao foi possivel ler os arquivos do pacote. Extraia o ZIP inteiro e tente novamente.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
