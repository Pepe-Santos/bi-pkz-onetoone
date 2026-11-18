"""Cartão do atleta no relatório: a nota ("over") e o valor de cada atributo, como no dashboard.

Mesmas regras do dashboard (frontend/catalogo_atributos.json e frontend/dashboard_atleta/cartao.py):
* cada atributo é o percentil (0 a 99) do último resultado do atleta no teste do atributo, entre ele e
  os colegas da mesma faixa de idade; só com pelo menos 5 resultados no grupo;
* simetria (SIM) = lado menor ÷ lado maior × 100 no teste dos dois lados; abaixo de 90 fica em alerta e
  não entra na nota;
* nota = média dos atributos preenchidos, sem a simetria; nos relatórios, com 2 ou mais atributos;
* nível e metal pela faixa da nota (E e D bronze, C prata, B ouro, A preto).
A nota é PROVISÓRIA: a fórmula definitiva é da escola. Tudo sai dos resultados do contrato.

One to One: os atributos da modalidade (FIN, RES, POT, FSU, COR, MOB) seguem as mesmas regras, entre colegas
do One to One. Enquanto não houver 2 desses atributos, o cartão usa os atributos de acompanhamento do período.
"""
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

from .contrato import ler_data

CATALOGO = Path(__file__).resolve().parents[2] / "frontend" / "catalogo_atributos.json"
# Nos relatórios, a nota sai com 2 ou mais atributos (pedido de 17/11/2026; o dashboard ainda usa 3).
MINIMO_DE_ATRIBUTOS = 2
INTENSIDADE = {"leve": 33, "baixa": 33, "moderada": 66, "media": 66, "média": 66, "alta": 100, "intensa": 100}


@lru_cache(maxsize=None)
def catalogo():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def _arredondar(v):
    return math.floor(v + 0.5)


def _percentil(valor, grupo, maior_melhor):
    abaixo = sum((v < valor) if maior_melhor else (v > valor) for v in grupo)
    iguais = sum(v == valor for v in grupo)
    return _arredondar(99 * (abaixo + 0.5 * iguais) / len(grupo))


def nivel_da_nota(nota):
    for regra in catalogo()["regras"]["niveis"]:
        if nota <= regra["ate"]:
            return regra["nivel"], regra["metal"]
    return "A", "Preto"


def _ultimos(registros, ate):
    """{(aluno, teste, lado): último valor até a data}."""
    saida = {}
    for r in sorted(registros, key=lambda r: r["data_avaliacao"]):
        if r.get("valor") is not None and ler_data(r["data_avaliacao"]) <= ate:
            saida[(r.get("aluno", "eu"), r["teste"], r.get("lado"))] = float(r["valor"])
    return saida


def calcular(contrato, ate):
    """Cartão PKZ até a data: atributos, nota, nível e metal (None quando não há base)."""
    cat = catalogo()
    modalidade = contrato["aluno"].get("modalidade")
    if contrato.get("modalidade") == "ONE_TO_ONE":
        definicoes, rotulo = cat["modalidades"]["ONE_TO_ONE"]["Todas"], "Nota"
    else:
        definicoes = cat["modalidades"]["PKZ"].get(modalidade) or cat["modalidades"]["GERAL"]
        rotulo = modalidade if modalidade in cat["modalidades"]["PKZ"] else "Nota"  # sem modalidade: atributos gerais
    regras = cat["regras"]
    meus = _ultimos([{**r, "aluno": "eu"} for r in contrato["avaliacoes"]], ate)
    grupo = _ultimos(contrato["grupo"]["avaliacoes"], ate)
    atributos = []
    for d in definicoes:
        valor = None
        if d["tipo"] == "percentil":
            eu = meus.get(("eu", d["teste"], None))
            colegas = [v for (a, t, l), v in grupo.items() if t == d["teste"] and l is None]
            if eu is not None and len(colegas) + 1 >= regras["minimo_no_grupo"]:
                valor = _percentil(eu, colegas + [eu], d["maior_melhor"])
        elif d["tipo"] == "simetria":
            dir_, esq = meus.get(("eu", d["teste"], "dir")), meus.get(("eu", d["teste"], "esq"))
            if dir_ and esq:
                valor = _arredondar(100 * min(dir_, esq) / max(dir_, esq))
        atributos.append({"sigla": d["sigla"], "nome": d["nome"], "valor": valor, "tipo": d["tipo"],
                          "alerta": d["tipo"] == "simetria" and valor is not None and valor < regras["simetria_minima"]})
    capacidades = [a["valor"] for a in atributos if a["tipo"] != "simetria" and a["valor"] is not None]
    nota = _arredondar(sum(capacidades) / len(capacidades)) if len(capacidades) >= MINIMO_DE_ATRIBUTOS else None
    nivel, metal = nivel_da_nota(nota) if nota is not None else (None, None)
    return {"atributos": atributos, "nota": nota, "nivel": nivel, "metal": metal, "rotulo": rotulo,
            "colegas": len({a for a, _, _ in grupo}), "minimo_para_nota": MINIMO_DE_ATRIBUTOS}


def calcular_one_to_one(contrato, inicio, fim):
    """Cartão do One to One: atributos da modalidade (testes físicos), como no dashboard, quando dão nota.

    Sem testes suficientes, atributos de acompanhamento de 0 a 100 tirados da chamada e dos treinos do período:

    FRQ frequência = presenças ÷ (presenças + faltas)
    CON constância = semanas com presença ÷ semanas com chamada (só com 2 ou mais semanas com chamada)
    REG treinos registrados = relatórios de treino ÷ presenças (no máximo 100)
    INT intensidade = média da intensidade registrada (leve 33, moderada 66, alta 100)
    Nota = média dos atributos calculados, com 2 ou mais.
    """
    fisico = calcular(contrato, fim)
    if fisico["nota"] is not None:
        return {**fisico, "origem": "fisico"}
    no_periodo = lambda lista: [x for x in lista if inicio <= ler_data(x["data"]) <= fim]
    sessoes, treinos = no_periodo(contrato["sessoes"]), no_periodo(contrato["treinos"])
    presentes = sum(s["status"] == "presente" for s in sessoes)
    faltas = sum(s["status"] == "falta" for s in sessoes)
    atributos = []
    if presentes + faltas:
        atributos.append(("FRQ", "Frequência", presentes / (presentes + faltas) * 100))
    semanas = {}
    for s in sessoes:
        if s["status"] in ("presente", "falta"):
            semana = ler_data(s["data"]).isocalendar()[:2]
            semanas[semana] = semanas.get(semana, False) or s["status"] == "presente"
    if len(semanas) >= 2:
        atributos.append(("CON", "Constância", sum(semanas.values()) / len(semanas) * 100))
    if presentes:
        atributos.append(("REG", "Treinos registrados", min(len(treinos) / presentes, 1) * 100))
    intensidades = [INTENSIDADE[(t.get("intensidade") or "").strip().lower()] for t in treinos
                    if (t.get("intensidade") or "").strip().lower() in INTENSIDADE]
    if intensidades:
        atributos.append(("INT", "Intensidade", sum(intensidades) / len(intensidades)))
    atributos = [{"sigla": s, "nome": n, "valor": _arredondar(v), "tipo": "acompanhamento", "alerta": v < 50} for s, n, v in atributos]
    nota = _arredondar(sum(a["valor"] for a in atributos) / len(atributos)) if len(atributos) >= MINIMO_DE_ATRIBUTOS else None
    nivel, metal = nivel_da_nota(min(nota, 99)) if nota is not None else (None, None)
    return {"atributos": atributos, "nota": nota, "nivel": nivel, "metal": metal, "rotulo": "Nota",
            "minimo_para_nota": MINIMO_DE_ATRIBUTOS, "origem": "acompanhamento"}


def evolucao_da_nota(contrato, inicio, fim):
    """Nota no começo do período (antes da 1ª avaliação dele, ou nela) e no fim, quando as duas existem."""
    datas = sorted({ler_data(r["data_avaliacao"]) for r in contrato["avaliacoes"] if inicio <= ler_data(r["data_avaliacao"]) <= fim})
    if not datas:
        return None
    antes = calcular(contrato, date.fromordinal(datas[0].toordinal() - 1))
    if antes["nota"] is None and len(datas) >= 2:  # sem nota antes do período: compara com a 1ª avaliação dele
        antes = calcular(contrato, datas[0])
    depois = calcular(contrato, fim)
    if antes["nota"] is None or depois["nota"] is None:
        return None
    return {"de": antes, "para": depois}
