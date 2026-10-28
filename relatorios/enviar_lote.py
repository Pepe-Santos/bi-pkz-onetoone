"""Gera e envia por e-mail os relatórios de um período para todos os alunos.

    python relatorios/enviar_lote.py --periodo mensal [--referencia 2026-08-26] [--limite 5] [--simular]

Para cada aluno das duas unidades (api.atleta): gera o PDF do período, guarda no bucket
privado relatorios do Supabase e envia com a enviar_email(). Aluno sem dados no período (o
gerador devolve None) é pulado. O que já foi enviado fica em trat.envio_relatorio
(backend/sql/07_trat_envio_relatorio.sql) e não é reenviado. Erro em um aluno é registrado
e o lote continua; no fim, o código de saída é 1 se algum aluno deu erro.

--referencia é qualquer dia do período (padrão: ontem, no fuso de São Paulo), então o
agendamento de segunda manda a semana anterior, o do dia 1º o mês anterior e o de 1º de
janeiro o ano anterior. --limite para depois de N envios; --simular só mostra o que seria
enviado, sem guardar, enviar nem registrar.

Modo teste (até a PKZ autorizar): todos os relatórios vão para EMAIL_LOTE_TESTE, que precisa
estar em EMAILS_TESTE, com [TESTE] e o nome do aluno no assunto.

Variáveis do backend/.env (veja backend/env.example): SUPABASE_DB_URL, SUPABASE_URL,
SUPABASE_SECRET_KEY e as do enviar_email.py, mais EMAIL_LOTE_TESTE.
"""

import argparse
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from functools import cache
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from enviar_email import ENV_PATH, emails_teste, enviar_email, montar_texto

BASE_DIR = Path(__file__).resolve().parent.parent
BUCKET = "relatorios"
PERIODOS = ("semanal", "mensal", "anual")
FUSO_SP = timezone(timedelta(hours=-3))  # São Paulo: sem horário de verão desde 2019
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro")

# O envio para o e-mail do responsável (PKZ) ou do próprio aluno (One to One) entra quando a
# PKZ autorizar e o cadastro tiver e-mail. Até lá, tudo vai para EMAIL_LOTE_TESTE.
MODO_TESTE = True


def calcular_periodo(periodo, referencia):
    """(início, fim, rótulo por extenso) do período que contém a data de referência."""
    if periodo == "semanal":
        inicio = referencia - timedelta(days=referencia.weekday())  # segunda-feira
        fim = inicio + timedelta(days=6)
        return inicio, fim, f"semana de {inicio:%d/%m} a {fim:%d/%m/%Y}"
    if periodo == "mensal":
        inicio = referencia.replace(day=1)
        fim = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return inicio, fim, f"{MESES[inicio.month - 1]} de {inicio.year}"
    return date(referencia.year, 1, 1), date(referencia.year, 12, 31), str(referencia.year)


def buscar_alunos(conexao):
    """Alunos das duas unidades, pela api.atleta (contrato em backend/docs/api.md).

    Pela conexão direta (sem token), a view mostra as duas unidades.
    """
    with conexao.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT atleta_id::text AS aluno_id, unidade, nome FROM api.atleta "
            "WHERE unidade IN ('PKZ', 'ONE_TO_ONE') ORDER BY unidade, nome"
        )
        return cursor.fetchall()


def ja_enviados(conexao, periodo, inicio):
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT aluno_id::text FROM trat.envio_relatorio "
            "WHERE periodo = %s AND inicio_periodo = %s AND teste = %s",
            (periodo, inicio, MODO_TESTE),
        )
        return {linha[0] for linha in cursor.fetchall()}


def registrar_envio(conexao, aluno, periodo, inicio, fim, arquivo):
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO trat.envio_relatorio "
            "(aluno_id, unidade, periodo, inicio_periodo, fim_periodo, teste, arquivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (aluno["aluno_id"], aluno["unidade"], periodo, inicio, fim, MODO_TESTE, arquivo),
        )


@cache
def pdf_exemplo():
    """PDF de exemplo do gerador do Henrique (dados fictícios de exemplos/api)."""
    sys.path.insert(0, str(BASE_DIR / "gerador_pkz"))
    import gerar_pdf

    gerar_pdf.gerar_relatorio()
    return next(gerar_pdf.SAIDA_DIR.glob("relatorio_pkz_*.pdf"))


def gerar_relatorio(conexao, aluno, inicio, fim):
    """Ponte com o gerador do Henrique: caminho do PDF, ou None se não há dado no período.

    Provisório até a versão por período (31/10): aluno da PKZ com avaliação no período recebe
    o PDF de exemplo; o One to One ainda não tem gerador e é pulado.
    """
    if aluno["unidade"] != "PKZ":
        return None
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM trat.resultado_teste "
            "WHERE aluno_id = %s AND data_avaliacao BETWEEN %s AND %s LIMIT 1",
            (aluno["aluno_id"], inicio, fim),
        )
        if cursor.fetchone() is None:
            return None
    return pdf_exemplo()


def guardar_no_bucket(caminho_pdf, destino):
    """Envia o PDF ao bucket privado (substitui se já existir) usando a secret key."""
    base = os.environ["SUPABASE_URL"].rstrip("/")
    secret = os.environ["SUPABASE_SECRET_KEY"]
    req = urllib.request.Request(
        f"{base}/storage/v1/object/{BUCKET}/{destino}",
        data=Path(caminho_pdf).read_bytes(),
        method="POST",
        headers={"apikey": secret, "Authorization": f"Bearer {secret}",
                 "Content-Type": "application/pdf", "x-upsert": "true"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60):
            pass
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"upload no bucket falhou ({erro.code}): {erro.read().decode()}") from None


def ler_argumentos():
    parser = argparse.ArgumentParser(description="Gera e envia os relatórios de um período.")
    parser.add_argument("--periodo", required=True, choices=PERIODOS)
    parser.add_argument("--referencia", type=date.fromisoformat,
                        help="AAAA-MM-DD, qualquer dia do período (padrão: ontem)")
    parser.add_argument("--limite", type=int, help="para depois de N envios")
    parser.add_argument("--simular", action="store_true",
                        help="só mostra o que seria enviado")
    return parser.parse_args()


def main():
    args = ler_argumentos()
    referencia = args.referencia or datetime.now(FUSO_SP).date() - timedelta(days=1)
    inicio, fim, rotulo = calcular_periodo(args.periodo, referencia)

    load_dotenv(ENV_PATH)
    necessarias = ["SUPABASE_DB_URL"]
    if not args.simular:
        necessarias += ["SUPABASE_URL", "SUPABASE_SECRET_KEY", "EMAIL_LOTE_TESTE"]
    faltando = [nome for nome in necessarias if not os.environ.get(nome)]
    if faltando:
        sys.exit(f"Faltam variáveis no backend/.env: {', '.join(faltando)}")
    destinatario = os.environ.get("EMAIL_LOTE_TESTE", "").strip()
    if not args.simular and destinatario.lower() not in emails_teste():
        sys.exit("EMAIL_LOTE_TESTE precisa estar em EMAILS_TESTE.")

    print(f"Relatório {args.periodo}: {rotulo} ({inicio} a {fim})"
          f"{' [simulação]' if args.simular else ''}")
    contagem = Counter()
    feito = "a enviar" if args.simular else "enviados"
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], autocommit=True) as conexao:
        enviados = ja_enviados(conexao, args.periodo, inicio)
        for aluno in buscar_alunos(conexao):
            if args.limite is not None and contagem[feito] >= args.limite:
                break
            if aluno["aluno_id"] in enviados:
                contagem["já enviados"] += 1
                continue
            try:
                pdf = gerar_relatorio(conexao, aluno, inicio, fim)
                if pdf is None:
                    contagem["sem dados"] += 1
                    continue
                if args.simular:
                    print(f"  enviaria: {aluno['unidade']} {aluno['aluno_id']}")
                    contagem[feito] += 1
                    continue
                arquivo = (f"{'teste/' if MODO_TESTE else ''}{aluno['unidade'].lower()}/"
                           f"{args.periodo}/{inicio}/{aluno['aluno_id']}.pdf")
                guardar_no_bucket(pdf, arquivo)
                nome = (aluno["nome"] or "aluno").split()[0]
                assunto, corpo = montar_texto(aluno["unidade"], nome, args.periodo, rotulo)
                if MODO_TESTE:
                    assunto = f"[TESTE · {aluno['nome']}] {assunto}"
                if not enviar_email(destinatario, assunto, corpo, pdf):
                    raise RuntimeError("destinatário recusado pelo modo teste")
                registrar_envio(conexao, aluno, args.periodo, inicio, fim, arquivo)
                contagem[feito] += 1
            except Exception as erro:  # um aluno com erro não para o lote
                contagem["erros"] += 1
                print(f"  [erro] aluno {aluno['aluno_id']}: {erro}")

    print("Resumo:", ", ".join(f"{n} {chave}" for chave, n in contagem.items()) or "nenhum aluno")
    sys.exit(1 if contagem["erros"] else 0)


if __name__ == "__main__":
    main()
