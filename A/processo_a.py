"""Duas janelas VS Code, duas depurações independentes: F9, F5 e F10."""
import os
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from psycopg.errors import SerializationFailure

def conectar():
    # Ignore configuracoes PG* herdadas somente neste processo Python.
    for chave in tuple(os.environ):
        if chave.startswith("PG"):
            os.environ.pop(chave, None)
    # O mesmo .env raiz atende A e B, mesmo abrindo em pastas diferentes.
    config = dotenv_values(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    return psycopg.connect(
        host=config.get("DB_HOST", "localhost"),
        port=int(config.get("DB_PORT", "5432")),
        dbname=config.get("DB_NAME", "transacao"),
        user=config.get("DB_USER", "postgres"),
        password=config.get("DB_PASSWORD", "ceub123456"),
        connect_timeout=5,
        options="",
        autocommit=True,
    )

def ler_saldo(conexao):
    saldo = conexao.execute(
        "SELECT saldo FROM lab_fluxo.conta WHERE id=1"
    ).fetchone()[0]
    print("Saldo lido:", saldo)
    return saldo

def calcular(saldo_lido, ajuste):
    saldo_novo = saldo_lido + ajuste
    print("Copia calculada:", saldo_novo)
    return saldo_novo

def gravar_saldo(conexao, saldo_novo):
    conexao.execute(
        "UPDATE lab_fluxo.conta SET saldo=%s WHERE id=1", (saldo_novo,)
    )

def consultar(conexao):
    contas = conexao.execute(
        "SELECT id, nome, saldo FROM lab_fluxo.conta ORDER BY id"
    ).fetchall()
    total = sum(conta[2] for conta in contas)
    print("Contas:", contas, "Total:", total)
    return contas, total

def iniciar(conexao):
    conexao.execute("BEGIN")

def confirmar(conexao):
    conexao.execute("COMMIT")

def desfazer(conexao):
    conexao.execute("ROLLBACK")

def iniciar_nivel(conexao, nivel):
    permitidos = ("READ UNCOMMITTED", "READ COMMITTED",
                  "REPEATABLE READ", "SERIALIZABLE")
    if nivel not in permitidos:
        raise ValueError("Use um dos quatro niveis escritos acima.")
    conexao.execute("BEGIN ISOLATION LEVEL " + nivel)

def alterar_saldo(conexao, ajuste):
    conexao.execute(
        "UPDATE lab_fluxo.conta SET saldo=saldo+%s WHERE id=1", (ajuste,)
    )

def debitar_ana(conexao):
    conexao.execute("UPDATE lab_fluxo.conta SET saldo=saldo-100 WHERE id=1")

def creditar_bruno(conexao):
    conexao.execute("UPDATE lab_fluxo.conta SET saldo=saldo+100 WHERE id=2")

def contar_plantao(conexao):
    ativos = conexao.execute(
        "SELECT count(*) FROM lab_fluxo.plantao WHERE ativo"
    ).fetchone()[0]
    print("Pessoas de plantao:", ativos)
    return ativos

def sair_do_plantao(conexao, pessoa):
    conexao.execute(
        "UPDATE lab_fluxo.plantao SET ativo=false WHERE id=%s", (pessoa,)
    )

def fechar(conexao):
    conexao.close()

def main():
    # Antes de F5: deixe só UM bloco ativo, salve e marque F9 na primeira linha dele.
    # Na outra janela, abra a outra pasta e inicie uma depuração independente.
    # F10 executa uma instrução; F11 opcional entra na função para examinar SQL.
    # Não envie seleções nem comandos ao Debug Console. Não edite durante a execução.
    # A senha vem do mesmo .env raiz nas duas janelas, sem pergunta no terminal.
    conexao = conectar()
    print("Banco e sessão:", conexao.info.dbname, conexao.info.backend_pid)
    conexao.execute("SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED")
    print("Nível padrão:", conexao.execute("SHOW default_transaction_isolation").fetchone()[0])
    consultar(conexao)  # Após reset: Ana 500, Bruno 300, Carla 500, total 1300.
    contar_plantao(conexao)  # Após reset: 2.

    # INICIO 1
    saldo_lido = ler_saldo(conexao)  # Ambos leem 500 antes de qualquer escrita.
    saldo_novo = calcular(saldo_lido, -100)  # A: 400; B: 550.
    gravar_saldo(conexao, saldo_novo)  # A confirma 400 automaticamente.
    consultar(conexao)  # Observação intermediária de A: Ana 400, antes da escrita de B.
    consultar(conexao)  # Observação final de A, F9: espere B gravar 550. Final 550, não 450.
    # FIM 1

    # INICIO 2A_SEM_BEGIN
    # debitar_ana(conexao)  # Não há crédito nesta rodada de interrupção.
    # consultar(conexao)  # Ana 400, Bruno 300, Carla 500, total 1200.
    # FIM 2A_SEM_BEGIN

    # INICIO 2A_ROLLBACK
    # iniciar(conexao)
    # debitar_ana(conexao)
    # consultar(conexao)  # A vê seu débito pendente: total 1200.
    # desfazer(conexao)  # F9 aqui: antes, B deve consultar e ver total 1300.
    # consultar(conexao)  # Ana 500, Bruno 300, Carla 500, total 1300.
    # FIM 2A_ROLLBACK

    # INICIO 2A_COMMIT
    # iniciar(conexao)
    # debitar_ana(conexao)
    # creditar_bruno(conexao)
    # confirmar(conexao)  # F9 aqui: B pode observar antes do COMMIT.
    # consultar(conexao)  # Ana 400, Bruno 400, Carla 500, total 1300.
    # FIM 2A_COMMIT

    # INICIO 2B
    # iniciar(conexao)
    # saldo_lido = ler_saldo(conexao)  # Ambos leem 500 antes de A escrever.
    # saldo_novo = calcular(saldo_lido, -100)
    # gravar_saldo(conexao, saldo_novo)
    # confirmar(conexao)  # F9: antes, B consulta e vê 500.
    # consultar(conexao)  # Observação intermediária após COMMIT de A: Ana 400.
    # consultar(conexao)  # Observação final de A, F9: espere B confirmar; final 550, não 450.
    # FIM 2B

    # INICIO 2C
    # iniciar(conexao)
    # alterar_saldo(conexao, -100)  # B aguarda na chamada; A deve confirmar para liberá-la.
    # confirmar(conexao)  # Em A, F9 aqui: dispare antes o UPDATE de B.
    # consultar(conexao)  # F9 em A: espere B confirmar. Final Ana 450.
    # FIM 2C

    # INICIO 3A_RU
    # iniciar_nivel(conexao, "READ UNCOMMITTED")
    # consultar(conexao)  # Primeira leitura 500; fixa snapshot nos dois níveis fortes.
    # consultar(conexao)  # F9: B já alterou, mas não confirmou. Ainda 500.
    # consultar(conexao)  # F9: B confirmou. RU/RC: 550; RR/SERIALIZABLE: 500.
    # confirmar(conexao)
    # consultar(conexao)  # Fora da transação: 550 nos quatro níveis.
    # FIM 3A_RU

    # INICIO 3A_RC
    # iniciar_nivel(conexao, "READ COMMITTED")
    # consultar(conexao)  # Primeira leitura 500; fixa snapshot nos dois níveis fortes.
    # consultar(conexao)  # F9: B já alterou, mas não confirmou. Ainda 500.
    # consultar(conexao)  # F9: B confirmou. RU/RC: 550; RR/SERIALIZABLE: 500.
    # confirmar(conexao)
    # consultar(conexao)  # Fora da transação: 550 nos quatro níveis.
    # FIM 3A_RC

    # INICIO 3A_RR
    # iniciar_nivel(conexao, "REPEATABLE READ")
    # consultar(conexao)  # Primeira leitura 500; fixa snapshot nos dois níveis fortes.
    # consultar(conexao)  # F9: B já alterou, mas não confirmou. Ainda 500.
    # consultar(conexao)  # F9: B confirmou. RU/RC: 550; RR/SERIALIZABLE: 500.
    # confirmar(conexao)
    # consultar(conexao)  # Fora da transação: 550 nos quatro níveis.
    # FIM 3A_RR

    # INICIO 3A_SER
    # iniciar_nivel(conexao, "SERIALIZABLE")
    # consultar(conexao)  # Primeira leitura 500; fixa snapshot nos dois níveis fortes.
    # consultar(conexao)  # F9: B já alterou, mas não confirmou. Ainda 500.
    # consultar(conexao)  # F9: B confirmou. RU/RC: 550; RR/SERIALIZABLE: 500.
    # confirmar(conexao)
    # consultar(conexao)  # Fora da transação: 550 nos quatro níveis.
    # FIM 3A_SER

    # INICIO 3B_RR
    # try:  # Descomente todo o bloco, incluindo except e recuperação.
    #     iniciar_nivel(conexao, "REPEATABLE READ")
    #     saldo_lido = ler_saldo(conexao)  # Ambos devem ler 500 antes de A escrever.
    #     saldo_novo = calcular(saldo_lido, -100)
    #     gravar_saldo(conexao, saldo_novo)  # B só avança após COMMIT de A: 40001.
    #     confirmar(conexao)
    # except SerializationFailure as erro:  # Só captura o erro esperado, inclusive no COMMIT.
    #     print("Tentativa rejeitada:", erro.sqlstate)  # Esperado: 40001.
    #     desfazer(conexao)  # Sem reset; preserve o trabalho já confirmado da outra sessão.
    #     iniciar_nivel(conexao, "REPEATABLE READ")
    #     saldo_lido = ler_saldo(conexao)  # Se A for rejeitada, relê o saldo já confirmado por B.
    #     saldo_novo = calcular(saldo_lido, -100)  # Refaz a decisão com o ajuste de A sobre a nova leitura.
    #     gravar_saldo(conexao, saldo_novo)
    #     confirmar(conexao)  # Outra falha não é ocultada; interrompa e investigue.
    # consultar(conexao)  # F9 em A: só avance após a recuperação de B. Final Ana 450.
    # FIM 3B_RR

    # INICIO 3C_RR
    # try:  # Descomente o bloco inteiro. A e B contam antes de qualquer saída.
    #     iniciar_nivel(conexao, "REPEATABLE READ")
    #     ativos = contar_plantao(conexao)  # Ambos guardam 2.
    #     if ativos > 1:  # B só avança após A confirmar, na ordem conduzida.
    #         sair_do_plantao(conexao, 1)
    #     confirmar(conexao)  # SERIALIZABLE pode rejeitar no UPDATE ou no COMMIT.
    # except SerializationFailure as erro:  # RR permite o write skew; SERIALIZABLE rejeita um.
    #     print("Tentativa rejeitada:", erro.sqlstate)
    #     desfazer(conexao)  # Não recoloque a pessoa já retirada pela sessão confirmada.
    #     iniciar_nivel(conexao, "REPEATABLE READ")
    #     ativos = contar_plantao(conexao)  # A vítima relê 1 e deve preservar a pessoa restante.
    #     if ativos > 1:  # Agora falso: não pode retirar o último plantonista.
    #         sair_do_plantao(conexao, 1)
    #     confirmar(conexao)  # Confirma também quando a decisão não faz UPDATE.
    # contar_plantao(conexao)  # F9 em A: espere B terminar. RR: 0; SERIALIZABLE: 1.
    # consultar(conexao)  # Contas não mudaram: total 1300.
    # FIM 3C_RR

    # INICIO 3B_SER
    # try:  # Descomente todo o bloco, incluindo except e recuperação.
    #     iniciar_nivel(conexao, "SERIALIZABLE")
    #     saldo_lido = ler_saldo(conexao)  # Ambos devem ler 500 antes de A escrever.
    #     saldo_novo = calcular(saldo_lido, -100)
    #     gravar_saldo(conexao, saldo_novo)  # B só avança após COMMIT de A: 40001.
    #     confirmar(conexao)
    # except SerializationFailure as erro:  # Só captura o erro esperado, inclusive no COMMIT.
    #     print("Tentativa rejeitada:", erro.sqlstate)  # Esperado: 40001.
    #     desfazer(conexao)  # Sem reset; preserve o trabalho já confirmado da outra sessão.
    #     iniciar_nivel(conexao, "SERIALIZABLE")
    #     saldo_lido = ler_saldo(conexao)  # Se A for rejeitada, relê o saldo já confirmado por B.
    #     saldo_novo = calcular(saldo_lido, -100)  # Refaz a decisão com o ajuste de A sobre a nova leitura.
    #     gravar_saldo(conexao, saldo_novo)
    #     confirmar(conexao)  # Outra falha não é ocultada; interrompa e investigue.
    # consultar(conexao)  # F9 em A: só avance após a recuperação de B. Final Ana 450.
    # FIM 3B_SER

    # INICIO 3C_SER
    # try:  # Descomente o bloco inteiro. A e B contam antes de qualquer saída.
    #     iniciar_nivel(conexao, "SERIALIZABLE")
    #     ativos = contar_plantao(conexao)  # Ambos guardam 2.
    #     if ativos > 1:  # B só avança após A confirmar, na ordem conduzida.
    #         sair_do_plantao(conexao, 1)
    #     confirmar(conexao)  # SERIALIZABLE pode rejeitar no UPDATE ou no COMMIT.
    # except SerializationFailure as erro:  # RR permite o write skew; SERIALIZABLE rejeita um.
    #     print("Tentativa rejeitada:", erro.sqlstate)
    #     desfazer(conexao)  # Não recoloque a pessoa já retirada pela sessão confirmada.
    #     iniciar_nivel(conexao, "SERIALIZABLE")
    #     ativos = contar_plantao(conexao)  # A vítima relê 1 e deve preservar a pessoa restante.
    #     if ativos > 1:  # Agora falso: não pode retirar o último plantonista.
    #         sair_do_plantao(conexao, 1)
    #     confirmar(conexao)  # Confirma também quando a decisão não faz UPDATE.
    # contar_plantao(conexao)  # F9 em A: espere B terminar. RR: 0; SERIALIZABLE: 1.
    # consultar(conexao)  # Contas não mudaram: total 1300.
    # FIM 3C_SER

    # Consultas finais estão no bloco, separadas do fechamento da conexão.
    # F9 na linha executável abaixo mantém esta conexão aberta se necessário.
    print("Checkpoint final: confira as duas janelas antes de fechar.")
    fechar(conexao)


if __name__ == "__main__":
    main()
