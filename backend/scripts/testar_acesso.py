"""Testa quem consegue ler a API de avaliações (schema api).

Roda os 3 testes do card "Proteger a API":
  1. sem login            -> não pode devolver dados
  2. com o usuário de teste -> devolve
  3. com a secret key      -> devolve

Só usa a biblioteca padrão. Lê as variáveis do backend/.env (veja backend/env.example).
Não imprime dados dos atletas: só o status HTTP e quantos atletas de cada unidade vieram
(o usuário só vê a unidade de app_metadata.unidade; veja 06_api_avaliacoes.sql).

    python backend/scripts/testar_acesso.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
VIEW = "atleta"


def carregar_env(caminho):
    """Lê KEY=valor do .env sem sobrescrever o que já está no ambiente."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def requisicao(metodo, url, cabecalhos, corpo=None):
    """Devolve (status, corpo em JSON ou texto)."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, headers=cabecalhos, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, texto = resp.status, resp.read().decode()
    except urllib.error.HTTPError as erro:
        status, texto = erro.code, erro.read().decode()
    try:
        return status, json.loads(texto)
    except json.JSONDecodeError:
        return status, texto


def login(base, publishable, email, senha):
    status, resp = requisicao(
        "POST",
        f"{base}/auth/v1/token?grant_type=password",
        {"apikey": publishable, "Content-Type": "application/json"},
        {"email": email, "password": senha},
    )
    if status != 200:
        print(f"  login falhou ({status}): {resp}")
        return None
    return resp["access_token"]


def ler_view(base, apikey, token=None):
    cabecalhos = {"apikey": apikey, "Accept-Profile": "api"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return requisicao("GET", f"{base}/rest/v1/{VIEW}?select=unidade", cabecalhos)


def descrever(status, resp):
    if status == 200 and isinstance(resp, list):
        unidades = {}
        for linha in resp:
            unidades[linha.get("unidade")] = unidades.get(linha.get("unidade"), 0) + 1
        por_unidade = ", ".join(f"{u}={n}" for u, n in sorted(unidades.items(), key=str))
        return f"{status}, {len(resp)} atleta(s) ({por_unidade or 'nenhum'})"
    if isinstance(resp, dict):
        if resp.get("code") == "PGRST106":
            return f"{status}, o schema api não está em Exposed schemas"
        mensagem = resp.get("message") or resp.get("msg") or resp.get("error")
        return f"{status}, {resp['code']}: {mensagem}" if resp.get("code") else f"{status}, {mensagem}"
    return f"{status}, {resp}"


def main():
    carregar_env(ENV_PATH)
    faltando = [
        nome
        for nome in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY",
                     "API_TESTE_EMAIL", "API_TESTE_SENHA")
        if not os.environ.get(nome)
    ]
    if faltando:
        sys.exit(f"Faltam variáveis no backend/.env: {', '.join(faltando)}")

    base = os.environ["SUPABASE_URL"].rstrip("/")
    publishable = os.environ["SUPABASE_PUBLISHABLE_KEY"]
    secret = os.environ["SUPABASE_SECRET_KEY"]

    resultados = []

    print("1. Sem login (só a publishable key)")
    status, resp = ler_view(base, publishable)
    ok = not (status == 200 and isinstance(resp, list) and resp)
    print(f"  {descrever(status, resp)}")
    resultados.append(("sem login não devolve dados", ok))

    print("2. Com o usuário de teste")
    token = login(base, publishable, os.environ["API_TESTE_EMAIL"], os.environ["API_TESTE_SENHA"])
    ok = False
    if token:
        status, resp = ler_view(base, publishable, token)
        ok = status == 200 and isinstance(resp, list) and len(resp) > 0
        print(f"  {descrever(status, resp)}")
    resultados.append(("com login devolve dados", ok))

    print("3. Com a secret key (gerador de relatórios)")
    status, resp = ler_view(base, secret, secret)
    ok = status == 200 and isinstance(resp, list) and len(resp) > 0
    print(f"  {descrever(status, resp)}")
    resultados.append(("com a secret key devolve dados", ok))

    print()
    for nome, ok in resultados:
        print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    sys.exit(0 if all(ok for _, ok in resultados) else 1)


if __name__ == "__main__":
    main()
