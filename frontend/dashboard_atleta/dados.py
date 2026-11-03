"""Leitura dos dados do dashboard: a API do Supabase ou, sem .env, os JSON de exemplo.

O contrato das views está em backend/docs/api.md.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

PASTA = Path(__file__).resolve().parent
EXEMPLOS = PASTA.parents[1] / "backend" / "exemplos" / "api"
VARIAVEIS = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "API_TESTE_EMAIL", "API_TESTE_SENHA")
LIMITE = 1000  # teto de linhas por chamada no Supabase
TEMPO_MAXIMO = 30

# Só para os exemplos, que não têm reavaliacao.json. Na API, as regras ficam em trat.parametro.
REAVALIACAO_DIAS = 90
REAVALIACAO_AVISO_DIAS = 30

load_dotenv(PASTA / ".env")


class ErroDados(Exception):
    """Falha ao ler os dados, com uma mensagem para mostrar na tela."""


def variaveis_faltando() -> list[str]:
    return [nome for nome in VARIAVEIS if not os.environ.get(nome)]


def usando_exemplos() -> bool:
    """Sem nenhuma credencial, usa os exemplos. Com o .env pela metade, a tela avisa o que falta."""
    return len(variaveis_faltando()) == len(VARIAVEIS)


# ---------------------------------------------------------------- API
_token: str | None = None


def _base() -> str:
    return os.environ["SUPABASE_URL"].rstrip("/")


def _login() -> str:
    try:
        resposta = requests.post(
            f"{_base()}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"]},
            json={"email": os.environ["API_TESTE_EMAIL"], "password": os.environ["API_TESTE_SENHA"]},
            timeout=TEMPO_MAXIMO,
        )
    except requests.RequestException as erro:
        raise ErroDados("Não consegui conectar ao Supabase. Confira a internet e o SUPABASE_URL.") from erro
    if resposta.status_code in (400, 401, 403):
        raise ErroDados("O Supabase recusou o login. Confira o e-mail, a senha e a chave no .env.")
    if not resposta.ok:
        raise ErroDados(f"O login no Supabase falhou (erro {resposta.status_code}).")
    return resposta.json()["access_token"]


def _chamar(view: str, params: dict) -> list[dict]:
    global _token
    for tentativa in (1, 2):
        _token = _token or _login()
        try:
            resposta = requests.get(
                f"{_base()}/rest/v1/{view}",
                params=params,
                headers={
                    "apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"],
                    "Authorization": f"Bearer {_token}",
                    "Accept-Profile": "api",
                },
                timeout=TEMPO_MAXIMO,
            )
        except requests.RequestException as erro:
            raise ErroDados("Não consegui conectar ao Supabase. Confira a internet e o SUPABASE_URL.") from erro
        if resposta.status_code == 401 and tentativa == 1:
            _token = None  # o token vale 1 hora: faz login de novo e repete
            continue
        if not resposta.ok:
            raise ErroDados(f"A API recusou a leitura da view {view} (erro {resposta.status_code}).")
        return resposta.json()
    raise ErroDados(f"A API recusou a leitura da view {view} (erro 401).")


def _ler_api(view: str, **filtros) -> list[dict]:
    linhas: list[dict] = []
    while True:
        pagina = _chamar(view, {**filtros, "limit": LIMITE, "offset": len(linhas)})
        linhas += pagina
        if len(pagina) < LIMITE:
            return linhas


# ---------------------------------------------------------------- exemplos
def _ler_exemplo(view: str) -> list[dict]:
    return json.loads((EXEMPLOS / f"{view}.json").read_text(encoding="utf-8"))


def _reavaliacao_de_exemplo() -> list[dict]:
    """Aplica aos exemplos a mesma regra da view reavaliacao."""
    linhas = []
    for atleta in _ler_exemplo("atleta"):
        if not atleta["ultima_avaliacao_em"]:
            continue
        vence_em = date.fromisoformat(atleta["ultima_avaliacao_em"]) + timedelta(days=REAVALIACAO_DIAS)
        dias = (vence_em - date.today()).days
        linhas.append({
            "atleta_id": atleta["atleta_id"],
            "unidade": atleta["unidade"],
            "ultima_avaliacao_em": atleta["ultima_avaliacao_em"],
            "vence_em": vence_em.isoformat(),
            "dias_para_vencer": dias,
            "situacao": "vencida" if dias < 0 else "a_vencer" if dias <= REAVALIACAO_AVISO_DIAS else "em_dia",
        })
    return linhas


def _do_atleta(linhas: list[dict], atleta_id: str) -> list[dict]:
    return [linha for linha in linhas if linha["atleta_id"] == atleta_id]


# ---------------------------------------------------------------- o que a tela usa
def atletas_pkz() -> list[dict]:
    if usando_exemplos():
        linhas = [a for a in _ler_exemplo("atleta") if a["unidade"] == "PKZ"]
        return sorted(linhas, key=lambda a: a["nome"])
    return _ler_api("atleta", unidade="eq.PKZ", order="nome.asc,atleta_id.asc")


def evolucao(atleta_id: str) -> list[dict]:
    if usando_exemplos():
        return sorted(_do_atleta(_ler_exemplo("evolucao"), atleta_id), key=lambda l: l["data_avaliacao"])
    return _ler_api("evolucao", atleta_id=f"eq.{atleta_id}",
                    order="data_avaliacao.asc,teste.asc,lado.asc")


def comparacao(atleta_id: str) -> list[dict]:
    if usando_exemplos():
        return _do_atleta(_ler_exemplo("comparacao"), atleta_id)
    return _ler_api("comparacao", atleta_id=f"eq.{atleta_id}", order="teste.asc,lado.asc")


def reavaliacoes_pkz() -> list[dict]:
    if usando_exemplos():
        linhas = [l for l in _reavaliacao_de_exemplo() if l["unidade"] == "PKZ"]
        return sorted(linhas, key=lambda l: l["dias_para_vencer"])
    return _ler_api("reavaliacao", unidade="eq.PKZ", order="dias_para_vencer.asc,atleta_id.asc")
