"""Gera e envia por e-mail os relatórios de um período para todos os alunos.

    python relatorios/enviar_lote.py --periodo mensal [--referencia 2026-08-26] [--limite 5] [--simular]

Para cada aluno das duas unidades (api.atleta): gera o PDF do período (gerador_pkz), guarda
no bucket privado relatorios do Supabase e envia com a enviar_email(). Aluno sem dados no
período (o gerador devolve None) é pulado. O que já foi enviado fica em trat.envio_relatorio
e não é reenviado. Erro em um aluno é registrado e o lote continua; no fim, o código de saída
é 1 se algum aluno deu erro.

Tudo passa pela API do Supabase com a secret key, sem a senha do banco: as views do schema
api, o Storage e as funções api.relatorios_enviados e api.registrar_envio_relatorio
(backend/sql/09_api_envio_relatorio.sql).

--referencia é qualquer dia do período (padrão: ontem, no fuso de São Paulo), então o
agendamento de segunda manda a semana anterior, o do dia 1º o mês anterior e o de 1º de
janeiro o ano anterior. --limite para depois de N envios; --simular gera os PDFs e mostra o
que seria enviado, sem guardar, enviar nem registrar.

Modo teste (até a PKZ autorizar): todos os relatórios vão para EMAIL_LOTE_TESTE, que precisa
estar em EMAILS_TESTE, com [TESTE] e o nome do aluno no assunto.

Variáveis do backend/.env (veja backend/env.example): SUPABASE_URL, SUPABASE_SECRET_KEY e as
do enviar_email.py, mais EMAIL_LOTE_TESTE.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

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


def chamar_supabase(metodo, caminho, corpo=None, cabecalhos=None):
    """Chamada à API do Supabase com a secret key. Devolve o JSON da resposta (ou None)."""
    secret = os.environ["SUPABASE_SECRET_KEY"]
    if isinstance(corpo, (dict, list)):
        corpo = json.dumps(corpo).encode()
        cabecalhos = {"Content-Type": "application/json", **(cabecalhos or {})}
    req = urllib.request.Request(
        f"{os.environ['SUPABASE_URL'].rstrip('/')}{caminho}",
        data=corpo,
        method=metodo,
        headers={"apikey": secret, "Authorization": f"Bearer {secret}", **(cabecalhos or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resposta:
            texto = resposta.read().decode()
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"{metodo} {caminho.split('?')[0]} falhou ({erro.code}): "
                           f"{erro.read().decode()[:300]}") from None
    return json.loads(texto) if texto else None


def buscar_alunos():
    """Alunos das duas unidades, pela api.atleta (contrato em backend/docs/api.md)."""
    filtros = urllib.parse.urlencode({
        "select": "atleta_id,unidade,nome",
        "unidade": "in.(PKZ,ONE_TO_ONE)",
        "order": "unidade,nome",
    })
    return chamar_supabase("GET", f"/rest/v1/atleta?{filtros}", cabecalhos={"Accept-Profile": "api"})


def ja_enviados(periodo, inicio):
    linhas = chamar_supabase(
        "POST", "/rest/v1/rpc/relatorios_enviados",
        {"periodo": periodo, "inicio_periodo": inicio.isoformat(), "teste": MODO_TESTE},
        {"Content-Profile": "api"},
    )
    return {linha["aluno_id"] for linha in linhas}


def registrar_envio(aluno, periodo, inicio, fim, arquivo):
    chamar_supabase(
        "POST", "/rest/v1/rpc/registrar_envio_relatorio",
        {"aluno_id": aluno["atleta_id"], "unidade": aluno["unidade"], "periodo": periodo,
         "inicio_periodo": inicio.isoformat(), "fim_periodo": fim.isoformat(),
         "teste": MODO_TESTE, "arquivo": arquivo},
        {"Content-Profile": "api"},
    )


def guardar_no_bucket(caminho_pdf, destino):
    """Envia o PDF ao bucket privado (substitui se já existir)."""
    chamar_supabase("POST", f"/storage/v1/object/{BUCKET}/{destino}", Path(caminho_pdf).read_bytes(),
                    {"Content-Type": "application/pdf", "x-upsert": "true"})


def gerar_relatorio(aluno, periodo, referencia):
    """Caminho do PDF do período, ou None se o aluno não tem dados nele.

    As duas unidades usam o gerador_pkz/gerar_pdf.py (Henrique): gerar_relatorio() para a PKZ
    e gerar_relatorio_one_to_one() para o One to One.
    """
    sys.path.insert(0, str(BASE_DIR / "gerador_pkz"))
    import gerar_pdf

    if aluno["unidade"] == "PKZ":
        return gerar_pdf.gerar_relatorio(aluno["atleta_id"], periodo, referencia)
    if aluno["unidade"] == "ONE_TO_ONE":
        return gerar_pdf.gerar_relatorio_one_to_one(aluno["atleta_id"], periodo, referencia)
    return None


def ler_argumentos():
    parser = argparse.ArgumentParser(description="Gera e envia os relatórios de um período.")
    parser.add_argument("--periodo", required=True, choices=PERIODOS)
    parser.add_argument("--referencia", type=date.fromisoformat,
                        help="AAAA-MM-DD, qualquer dia do período (padrão: ontem)")
    parser.add_argument("--limite", type=int, help="para depois de N envios")
    parser.add_argument("--simular", action="store_true",
                        help="gera os PDFs e mostra o que seria enviado, sem enviar")
    return parser.parse_args()


def main():
    args = ler_argumentos()
    referencia = args.referencia or datetime.now(FUSO_SP).date() - timedelta(days=1)
    inicio, fim, rotulo = calcular_periodo(args.periodo, referencia)

    load_dotenv(ENV_PATH)
    necessarias = ["SUPABASE_URL", "SUPABASE_SECRET_KEY"]
    if not args.simular:
        necessarias.append("EMAIL_LOTE_TESTE")
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
    enviados = ja_enviados(args.periodo, inicio)
    for aluno in buscar_alunos():
        if args.limite is not None and contagem[feito] >= args.limite:
            break
        if aluno["atleta_id"] in enviados:
            contagem["já enviados"] += 1
            continue
        try:
            pdf = gerar_relatorio(aluno, args.periodo, referencia)
            if pdf is None:
                contagem["sem dados"] += 1
                continue
            if args.simular:
                print(f"  enviaria: {aluno['unidade']} {aluno['atleta_id']}")
                contagem[feito] += 1
                continue
            arquivo = (f"{'teste/' if MODO_TESTE else ''}{aluno['unidade'].lower()}/"
                       f"{args.periodo}/{inicio}/{aluno['atleta_id']}.pdf")
            guardar_no_bucket(pdf, arquivo)
            nome = (aluno["nome"] or "aluno").split()[0]
            assunto, corpo = montar_texto(aluno["unidade"], nome, args.periodo, rotulo)
            if MODO_TESTE:
                assunto = f"[TESTE · {aluno['nome']}] {assunto}"
            if not enviar_email(destinatario, assunto, corpo, pdf):
                raise RuntimeError("destinatário recusado pelo modo teste")
            registrar_envio(aluno, args.periodo, inicio, fim, arquivo)
            contagem[feito] += 1
        except Exception as erro:  # um aluno com erro não para o lote
            contagem["erros"] += 1
            print(f"  [erro] aluno {aluno['atleta_id']}: {erro}")

    print("Resumo:", ", ".join(f"{n} {chave}" for chave, n in contagem.items()) or "nenhum aluno")
    sys.exit(1 if contagem["erros"] else 0)


if __name__ == "__main__":
    main()
