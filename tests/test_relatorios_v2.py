"""Testes dos relatórios v2 (3, 4 e 5 páginas).

Os contratos daqui são montados só para exercitar o código (volumes e faltas de dado diferentes).
Eles nunca alimentam um relatório entregue: os PDFs reais saem de contratos com dados da API.
"""
import csv
from datetime import date, timedelta

import pytest
from pypdf import PdfReader

from gerador_pkz.v2 import PAGINAS
from gerador_pkz.v2 import contrato as C
from gerador_pkz.v2 import fontes as F
from gerador_pkz.v2 import indicadores as I
from gerador_pkz.v2 import render as R

HOJE = date(2026, 11, 17)
REF = {"semanal": date(2026, 8, 17), "mensal": date(2026, 8, 1), "anual": date(2026, 1, 1)}


def contrato(modalidade, tipo, sessoes=(), avaliacoes=(), treinos=(), grupo=(), **aluno):
    ini, fim = C.periodo_padrao(tipo, REF[tipo])
    return {"modalidade": modalidade, "tipo_relatorio": tipo, "periodo": {"inicio": ini.isoformat(), "fim": fim.isoformat()},
            "aluno": {"nome": "Teste Automatizado", "idade": 12, **aluno}, "sessoes": list(sessoes), "avaliacoes": list(avaliacoes),
            "treinos": list(treinos), "grupo": {"descricao": "colegas", "avaliacoes": list(grupo)}}


def sessoes(inicio, dias, padrao=("presente", "presente", "falta", "cancelado", "agendado")):
    return [{"data": (inicio + timedelta(days=i)).isoformat(), "hora_inicio": "08:00", "status": padrao[i % len(padrao)]}
            for i in range(dias)]


def avaliacoes(datas, testes=8, confirmado=True):
    regs = []
    for k, d in enumerate(datas):
        for t in range(testes):
            regs.append({"avaliacao_id": f"a{k}", "data_avaliacao": d.isoformat(), "teste": f"teste_{t}", "teste_nome": f"Teste número {t}",
                         "lado": None, "unidade_medida": "s" if t % 2 else "cm", "maior_melhor": bool(t % 2 == 0),
                         "confirmado": confirmado, "valor": 10 + t + k * (1 if t % 3 else -1)})
    return regs


def treinos(inicio, n):
    return [{"data": (inicio + timedelta(days=i % 28)).isoformat(), "intensidade": ["Alta", "Moderada", "Leve"][i % 3],
             "desempenho": "Executou todas as séries" if i % 2 else "Completou parcialmente", "observacoes": None if i % 4 else "Boa execução."}
            for i in range(n)]


# ---------------------------------------------------------------- validação
def test_periodo_precisa_ser_completo():
    c = contrato("PKZ", "mensal", sessoes(date(2026, 8, 3), 3))
    c["periodo"]["inicio"] = "2026-08-05"
    _, erros, _ = C.validar(c, HOJE)
    assert any("mês completo" in e for e in erros)


@pytest.mark.parametrize("campo,valor,trecho", [
    ("status", "talvez", "status desconhecido"),
    ("data", "31/02/2026", "data inválida"),
])
def test_sessao_invalida_e_erro(campo, valor, trecho):
    s = sessoes(date(2026, 8, 3), 2)
    s[0][campo] = valor
    _, erros, _ = C.validar(contrato("PKZ", "mensal", s), HOJE)
    assert any(trecho in e for e in erros)


def test_presenca_no_futuro_e_erro():
    _, erros, _ = C.validar(contrato("PKZ", "anual", [{"data": "2026-12-20", "status": "presente"}, *sessoes(date(2026, 8, 3), 2)]), HOJE)
    assert any("data futura" in e for e in erros)


def test_unidades_diferentes_no_mesmo_teste_e_erro():
    a = avaliacoes([date(2026, 8, 5)], testes=1)
    b = dict(a[0], avaliacao_id="b", data_avaliacao="2026-08-20", unidade_medida="m")
    _, erros, _ = C.validar(contrato("PKZ", "mensal", avaliacoes=a + [b]), HOJE)
    assert any("unidades diferentes" in e for e in erros)


def test_registro_repetido_conta_uma_vez():
    s = sessoes(date(2026, 8, 3), 1) * 2
    c, erros, avisos = C.validar(contrato("PKZ", "mensal", s), HOJE)
    assert not erros and len(c["sessoes"]) == 1 and any("repetido" in a for a in avisos)


def test_texto_de_demonstracao_nao_vira_dado():
    t = treinos(date(2026, 8, 3), 2)
    t[0]["desempenho"] = "Dado fictício de demonstração — informação original não disponível"
    c, _, _ = C.validar(contrato("ONE_TO_ONE", "mensal", sessoes(date(2026, 8, 3), 2), treinos=t), HOJE)
    assert c["treinos"][0]["desempenho"] is None


def test_sem_registro_no_periodo_nao_gera():
    _, erros, _ = C.validar(contrato("PKZ", "mensal", [{"data": "2026-06-02", "status": "presente"}]), HOJE)
    assert any("não há relatório" in e for e in erros)


# ---------------------------------------------------------------- cálculos
def test_frequencia_ignora_cancelada_e_agendada():
    s = [{"data": "2026-08-03", "status": "presente"}, {"data": "2026-08-04", "status": "falta"},
         {"data": "2026-08-05", "status": "cancelado"}, {"data": "2026-08-06", "status": "agendado"}]
    ind = I.calcular(C.validar(contrato("PKZ", "mensal", s), HOJE)[0], HOJE)
    assert ind["sessoes"]["frequencia"] == 50 and ind["sessoes"]["total"] == 4


def test_frequencia_sem_chamada_e_sem_registro_nunca_zero():
    ind = I.calcular(C.validar(contrato("PKZ", "mensal", [{"data": "2026-08-06", "status": "cancelado"}]), HOJE)[0], HOJE)
    assert ind["sessoes"]["frequencia"] is None


def test_teste_de_tempo_menor_e_melhor():
    assert I.situacao(3.5, 3.3, False)[0] == "melhorou"
    assert I.situacao(30, 33, True)[0] == "melhorou"
    assert I.situacao(30, 30.3, True)[0] == "estavel"


def test_contagem_pequena_nao_vira_percentual():
    sit, var = I.situacao(1, 0, False)
    assert sit == "melhorou" and var is None


def test_regra_em_validacao_mostra_valores_sem_classificar():
    a = avaliacoes([date(2026, 6, 1), date(2026, 8, 5)], testes=2, confirmado=False)
    ind = I.calcular(C.validar(contrato("PKZ", "mensal", avaliacoes=a), HOJE)[0], HOJE)
    t = ind["testes"][0]
    assert t["situacao"] == "em_validacao" and t["atual"] is not None and t["anterior"] is not None


def test_posicao_no_grupo_so_com_cinco_colegas():
    a = avaliacoes([date(2026, 8, 5)], testes=1)
    grupo = [{"aluno": f"c{i}", "teste": "teste_0", "lado": None, "data_avaliacao": "2026-08-05", "valor": 5 + i,
              "confirmado": True, "maior_melhor": True} for i in range(4)]
    ind = I.calcular(C.validar(contrato("PKZ", "mensal", avaliacoes=a, grupo=grupo), HOJE)[0], HOJE)
    assert ind["testes"][0]["grupo"] is None
    grupo.append(dict(grupo[0], aluno="c9"))
    ind = I.calcular(C.validar(contrato("PKZ", "mensal", avaliacoes=a, grupo=grupo), HOJE)[0], HOJE)
    assert ind["testes"][0]["grupo"]["colegas"] == 5


# ---------------------------------------------------------------- ficha de matrícula
def test_ficha_descarta_dados_pessoais(tmp_path):
    arquivo = tmp_path / "ficha.csv"
    with arquivo.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Carimbo de data/hora", "Nome Completo Aluno", "Data de Nascimento", "Turno escolar", "Esporte/Modalidade",
                    "Clube/ Escolinha", "CPF do responsável", "Telefone para contato", "E-mail do responsável "])
        w.writerow(["x", "Teste Automatizado", "10/03/2014", "Manhã", "Futebol", "Clube X", "000.000.000-00", "(21) 0000-0000", "a@b.c"])
    fichas = F.ler_ficha(arquivo)
    registro = fichas["teste automatizado"]
    assert set(registro) == {"nascimento", "modalidade", "clube", "turno"}
    c = contrato("PKZ", "mensal", sessoes(date(2026, 8, 3), 2))
    F.aplicar_ficha(c, fichas, hoje=HOJE)
    assert c["aluno"]["data_nascimento"] == "2014-03-10" and c["aluno"]["idade"] == 12 and c["aluno"]["clube"] == "Clube X"
    assert "000.000.000-00" not in str(c)


# ---------------------------------------------------------------- páginas: quantidade fixa e nada cortado
VOLUMES = {
    "minimo": lambda u, t: contrato(u, t, sessoes(REF[t] + timedelta(days=1), 1, ("presente",))),
    "so_avaliacao": lambda u, t: contrato(u, t, avaliacoes=avaliacoes([REF[t] + timedelta(days=2)], 3)) if u == "PKZ"
    else contrato(u, t, treinos=treinos(REF[t] + timedelta(days=1), 1)),
    "cheio": lambda u, t: contrato(u, t, sessoes(REF[t], {"semanal": 7, "mensal": 31, "anual": 300}[t]),
                                   avaliacoes=avaliacoes([REF[t] - timedelta(days=200), REF[t] + timedelta(days=2), REF[t] + timedelta(days=5)], 30),
                                   treinos=treinos(REF[t], {"semanal": 7, "mensal": 40, "anual": 200}[t])),
}


@pytest.mark.parametrize("volume", list(VOLUMES))
@pytest.mark.parametrize("tipo", C.TIPOS)
@pytest.mark.parametrize("unidade", ["PKZ", "ONE_TO_ONE"])
def test_paginas_ate_o_maximo_e_sem_conteudo_cortado(unidade, tipo, volume, tmp_path):
    pdf, _, problemas = R.gerar_pdf(VOLUMES[volume](unidade, tipo), tmp_path / "r.pdf", hoje=HOJE)
    leitor = PdfReader(str(pdf))
    assert 1 <= len(leitor.pages) <= PAGINAS[tipo] and not problemas
    for pagina in leitor.pages:
        assert float(pagina.mediabox.width) == pytest.approx(595.3, abs=1) and float(pagina.mediabox.height) == pytest.approx(841.9, abs=1)
    texto = " ".join(p.extract_text() for p in leitor.pages)
    assert "Teste Automatizado" in texto and "demonstração" not in texto


# ---------------------------------------------------------------- cartão do One to One
def _testes_oto(valor_eu, data):
    from gerador_pkz.v2 import cartao as K
    defs = [d for d in K.catalogo()["modalidades"]["ONE_TO_ONE"]["Todas"] if d["tipo"] == "percentil"][:2]
    meus = [{"avaliacao_id": "a", "data_avaliacao": data, "teste": d["teste"], "teste_nome": d["nome"], "lado": None,
             "unidade_medida": "un", "maior_melhor": True, "confirmado": True, "valor": valor_eu} for d in defs]
    grupo = [{"aluno": f"colega-{i}", "teste": d["teste"], "lado": None, "data_avaliacao": data, "valor": 10 + i,
              "confirmado": True, "maior_melhor": True} for d in defs for i in range(5)]
    return defs, meus, grupo


def test_one_to_one_usa_atributos_da_modalidade_com_testes(tmp_path):
    from gerador_pkz.v2 import cartao as K
    defs, meus, grupo = _testes_oto(100, "2026-08-18")
    c = contrato("ONE_TO_ONE", "semanal", sessoes(REF["semanal"], 5), meus, grupo=grupo)
    ini, fim = C.periodo_padrao("semanal", REF["semanal"])
    k = K.calcular_one_to_one(c, ini, fim)
    assert k["origem"] == "fisico"
    assert [a["sigla"] for a in k["atributos"]] == [d["sigla"] for d in K.catalogo()["modalidades"]["ONE_TO_ONE"]["Todas"]]
    preenchidos = [a["valor"] for a in k["atributos"] if a["valor"] is not None]
    assert len(preenchidos) == 2 and k["nota"] == round(sum(preenchidos) / 2)
    # o relatório completo sai com o cartão da modalidade, sem conteúdo cortado
    _, _, problemas = R.gerar_pdf(c, tmp_path / "r.pdf", hoje=HOJE)
    html = R.montar_html(C.validar_ou_falhar(c, HOJE)[0], HOJE)[0]
    assert not problemas and f"<span>{defs[0]['sigla']}</span>" in html and "<span>FRQ</span>" not in html


def test_one_to_one_sem_testes_usa_acompanhamento():
    from gerador_pkz.v2 import cartao as K
    c = contrato("ONE_TO_ONE", "mensal", sessoes(REF["mensal"], 20), treinos=treinos(REF["mensal"], 6))
    ini, fim = C.periodo_padrao("mensal", REF["mensal"])
    k = K.calcular_one_to_one(c, ini, fim)
    assert k["origem"] == "acompanhamento" and {a["sigla"] for a in k["atributos"]} <= {"FRQ", "CON", "REG", "INT"}
    assert k["nota"] is not None


# ---------------------------------------------------------------- redimensionamento
@pytest.mark.parametrize("volume", list(VOLUMES))
@pytest.mark.parametrize("tipo", C.TIPOS)
@pytest.mark.parametrize("unidade", ["PKZ", "ONE_TO_ONE"])
def test_nenhum_bloco_cresce_alem_do_conteudo(unidade, tipo, volume):
    """Bloco que sobra numa linha (ex.: rosca sozinha) não estica até ocupar a folha."""
    from gerador_pkz.v2 import paginas as P
    ind = I.calcular(C.validar_ou_falhar(VOLUMES[volume](unidade, tipo), HOJE)[0], HOJE)
    for pagina in P.montar(P.paginas(ind)):
        for l in pagina["linhas"]:
            if isinstance(l["altura"], float) and (maxima := P._maxima_da_linha(l)) is not None:
                assert l["px"] <= max(maxima, l["minimo"]) + 1, (pagina["titulo"], [b.get("titulo") for b in l["blocos"]], l["px"])
            for b in l["blocos"]:
                if b.get("maximo") == P.ROSCA["maximo"]:
                    assert l["px"] <= P.ROSCA["maximo"] + 1 or len(l["blocos"]) > 1
