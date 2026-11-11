"""Testes do renderizador HTML (Jinja2 + Playwright). Somente dados sintéticos."""
import copy
import re
import sys
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sinteticos as S  # noqa: E402

from gerador_pkz import contexto_relatorio as cr  # noqa: E402
from gerador_pkz import render_html as R  # noqa: E402

PERIODOS = ["semanal", "mensal", "anual"]
SEIS = [(u, p) for u in ("PKZ", "ONE_TO_ONE") for p in PERIODOS]
REPO = Path(__file__).resolve().parents[1]

# Textos e números de demonstração dos modelos oficiais: nunca podem aparecer num relatório real.
DEMO = [
    "Igor", "Marina", "Rafael Lima", "Meio-campo", "Futebol de Campo", "Duarte Alencar",
    "456,8", "13,6 t", "143/152", "97/112", "14/16", "CREF 0000", "1RM", "PSE", "tonelagem",
    "Tonelagem", "carga aguda", "VO₂", "prata", "Relatos de desconforto", "Mensagem do professor",
    "Leitura do treinador", "Queixas de dor", "Próxima semana", "Próxima avaliação",
]


def contexto(unidade, periodo, **troca):
    if unidade == "PKZ":
        atleta, ev, pr = S.pkz_sintetico()
        dados = {"evolucoes": ev, "presencas": pr, **troca}
        return R.montar_contexto(unidade, atleta, periodo, S.REFERENCIA, **dados)
    atleta, pr, tr = S.o2o_sintetico()
    dados = {"presencas": pr, "treinos": tr, **troca}
    return R.montar_contexto(unidade, atleta, periodo, S.REFERENCIA, **dados)


def html(unidade, periodo, **troca):
    return R.renderizar_html(contexto(unidade, periodo, **troca))


def texto_visivel(documento):
    sem_estilo = re.sub(r"<style.*?</style>", "", documento, flags=re.S)
    return re.sub(r"<[^>]+>", " ", sem_estilo)


# ------------------------------------------------------------ seleção de template
@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_seleciona_o_template_correto_para_cada_unidade_e_periodo(unidade, periodo):
    esperado = f"{'PKZ' if unidade == 'PKZ' else 'OneToOne'}_relatorio_{periodo}.html"
    assert cr.nome_template(unidade, periodo) == esperado
    assert (REPO / "templates" / esperado).exists()
    ctx = contexto(unidade, periodo)
    assert ctx["template"] == esperado
    assert f'data-template="{esperado}"' in R.renderizar_html(ctx)


def test_periodo_invalido_e_rejeitado():
    with pytest.raises(ValueError):
        cr.nome_template("PKZ", "diario")


def test_seis_modelos_oficiais_de_referencia_estao_no_repositorio():
    nomes = sorted(p.name for p in (REPO / "templates" / "referencia").glob("*.html"))
    assert nomes == sorted(f"{u}_relatorio_{p}.html" for u in ("PKZ", "OneToOne") for p in PERIODOS)


# ------------------------------------------------------------------ preenchimento
@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_campos_do_atleta_e_periodo_sao_preenchidos(unidade, periodo):
    saida = html(unidade, periodo)
    nome = "Atleta Exemplo Sintético" if unidade == "PKZ" else "Aluno Exemplo Sintético"
    assert nome in saida
    assert {"semanal": "24/08 a 30/08", "mensal": "Agosto de 2026", "anual": "2026"}[periodo] in saida
    assert "{{" not in saida and "{%" not in saida


def test_pkz_mostra_resultados_reais_dos_testes():
    saida = html("PKZ", "mensal")
    for esperado in ("Sprint 20 m", "3,30 s", "3,45 s", "Salto vertical", "35,00 cm", "Força de preensão (dir)"):
        assert esperado in saida


def test_one_to_one_mostra_treinos_reais():
    saida = html("ONE_TO_ONE", "mensal")
    assert "Força inferiores" in saida and "Executou todas as séries" in saida
    assert "Histórico de treinos do mês" in saida


# ----------------------------------------------------- substituição dos dados demo
@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_nenhum_dado_de_demonstracao_dos_modelos_aparece(unidade, periodo):
    visivel = texto_visivel(html(unidade, periodo))
    for demo in DEMO:
        assert demo not in visivel, f"dado de demonstração vazou: {demo!r}"


@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_html_nao_depende_de_internet(unidade, periodo):
    saida = html(unidade, periodo)
    assert "googleapis" not in saida and "http://" not in saida and "https://" not in saida
    assert "@font-face" in saida and "data:font/ttf;base64" in saida
    assert "data:image/png;base64" in saida


@pytest.mark.parametrize("periodo", PERIODOS)
def test_one_to_one_nunca_exibe_informacao_de_dor(periodo):
    atleta, pr, tr = S.o2o_sintetico()
    for t in tr:  # mesmo que o texto livre mencione dor, o relatório não usa esses campos
        t["observacoes"] = "relatou dor no joelho"
    visivel = texto_visivel(R.renderizar_html(R.montar_contexto(
        "ONE_TO_ONE", atleta, periodo, S.REFERENCIA, presencas=pr, treinos=tr)))
    assert not re.search(r"\bdor\b|desconforto|queixa|lesão|joelho", visivel, flags=re.I)


# ------------------------------------------------------------- informações ausentes
def test_pkz_sem_presencas_oculta_blocos_de_frequencia():
    ctx = contexto("PKZ", "mensal", presencas=[])
    saida = R.renderizar_html(ctx)
    assert ctx["numeros"][0]["rotulo"] == "Avaliações"
    assert "Presença semana a semana" not in saida
    assert "Faltas" not in saida and "Frequência" not in saida


def test_pkz_sem_avaliacoes_mostra_apenas_presenca_e_nao_inventa_testes():
    ctx = contexto("PKZ", "mensal", evolucoes=[])
    saida = R.renderizar_html(ctx)
    assert ctx["comparacoes"] == [] and ctx["evolucao"] == []
    assert "Resultados dos testes" not in saida and "Evolução em cada teste" not in saida
    assert ctx["card"]["itens"] == []
    assert "Presença semana a semana" in saida


def test_one_to_one_sem_detalhes_de_treino_mostra_aviso_sem_inventar():
    atleta, pr, tr = S.o2o_sintetico()
    for t in tr:
        t.update({"tipo_treino": None, "intensidade": "", "objetivos": None, "desempenho": None})
    ctx = R.montar_contexto("ONE_TO_ONE", atleta, "mensal", S.REFERENCIA, presencas=pr, treinos=tr)
    saida = R.renderizar_html(ctx)
    assert ctx["treinos_campos"] == [] and ctx["distribuicoes"] == []
    assert "ainda não estão registrados" in saida
    assert "Tipo de treino" not in saida


def test_one_to_one_descarta_texto_demonstrativo_de_treino():
    atleta, pr, tr = S.o2o_sintetico()
    tr[-1]["desempenho"] = "Dado ficticio de demonstracao"
    ctx = R.montar_contexto("ONE_TO_ONE", atleta, "semanal", S.REFERENCIA, presencas=pr, treinos=tr)
    assert "demonstra" not in texto_visivel(R.renderizar_html(ctx)).lower()


@pytest.mark.parametrize("unidade", ["PKZ", "ONE_TO_ONE"])
def test_sem_dados_no_periodo_nao_gera_contexto_nem_pdf(unidade, tmp_path):
    if unidade == "PKZ":
        atleta, _, _ = S.pkz_sintetico()
        assert R.montar_contexto(unidade, atleta, "mensal", date(2025, 1, 15), evolucoes=[], presencas=[]) is None
    else:
        atleta, _, _ = S.o2o_sintetico()
        assert R.montar_contexto(unidade, atleta, "mensal", date(2025, 1, 15), presencas=[], treinos=[]) is None


# --------------------------------------------------------------------- indicadores
def test_frequencia_considera_apenas_presencas_e_faltas():
    c = cr.contar_status([{"status": s} for s in
                          ["presente"] * 6 + ["falta"] * 2 + ["cancelado"] * 5 + ["agendado", "aguardando_confirmacao"]])
    assert (c["presentes"], c["faltas"], c["cancelados"], c["agendados"]) == (6, 2, 5, 2)
    assert c["percentual"] == pytest.approx(75.0)
    assert cr.contar_status([{"status": "cancelado"}])["percentual"] is None


def test_variacao_e_situacao_respeitam_maior_melhor():
    ctx = contexto("PKZ", "mensal")
    por_nome = {c["nome"]: c for c in ctx["comparacoes"]}
    sprint = por_nome["Sprint 20 m"]  # menor é melhor: 3,45 -> 3,30
    assert sprint["situacao"] == "melhorou" and sprint["variacao"] == "-4,3%" and sprint["menor_melhor"]
    salto = por_nome["Salto vertical"]  # maior é melhor: 33,5 -> 35
    assert salto["situacao"] == "melhorou" and salto["variacao"] == "+4,5%"
    agil = por_nome["Agilidade em T"]  # menor é melhor: 11,0 -> 11,5
    assert agil["situacao"] == "piorou"
    assert por_nome["Força de preensão (dir)"]["situacao"] == "estavel"


def test_resultado_nao_confirmado_aparece_como_em_validacao_sem_expor_valor():
    ctx = contexto("PKZ", "mensal")
    flex = next(c for c in ctx["comparacoes"] if c["nome"] == "Flexibilidade")
    assert flex["situacao_texto"] == "Em validação" and flex["atual"] == "Em validação" and flex["variacao"] is None
    saida = R.renderizar_html(ctx)
    assert "15,00 cm" not in saida  # valor ainda não confirmado
    assert all(e["nome"] != "Flexibilidade" for e in ctx["evolucao"])  # e fora dos gráficos
    assert ctx["em_validacao"] == ["Flexibilidade"]


def test_comparacao_respeita_data_de_referencia_e_nao_mistura_periodos():
    # em maio só existem as medições de março e maio; a de agosto não pode entrar
    atleta, ev, pr = S.pkz_sintetico()
    ctx = R.montar_contexto("PKZ", atleta, "mensal", date(2026, 5, 29), evolucoes=ev, presencas=pr)
    sprint = next(c for c in ctx["comparacoes"] if c["nome"] == "Sprint 20 m")
    assert sprint["anterior"] == "3,60 s" and sprint["atual"] == "3,45 s"
    assert "3,30" not in R.renderizar_html(ctx)
    # em julho nenhum teste foi medido: sem comparações, mesmo havendo histórico
    ctx_jul = R.montar_contexto("PKZ", atleta, "mensal", date(2026, 7, 15), evolucoes=ev, presencas=pr)
    assert ctx_jul["comparacoes"] == []
    # semana de agosto sem avaliação no período também não traz testes antigos
    ctx_sem = R.montar_contexto("PKZ", atleta, "semanal", date(2026, 8, 12), evolucoes=ev, presencas=pr)
    assert ctx_sem["comparacoes"] == []


def test_zero_anterior_nao_inventa_percentual():
    atleta, ev, pr = S.pkz_sintetico()
    ev = [dict(e, valor=0.0) if e["teste"] == "salto_cmj" and e["data_avaliacao"] == "2026-05-22" else e for e in ev]
    ctx = R.montar_contexto("PKZ", atleta, "mensal", S.REFERENCIA, evolucoes=ev, presencas=pr)
    salto = next(c for c in ctx["comparacoes"] if c["nome"] == "Salto vertical")
    assert salto["variacao"] is None


def test_unidade_one_to_one_anual_mostra_dez_treinos_e_total_do_periodo():
    atleta, pr, tr = S.o2o_sintetico()
    ctx = R.montar_contexto("ONE_TO_ONE", atleta, "anual", S.REFERENCIA, presencas=pr, treinos=tr)
    assert len(ctx["treinos"]) == 10 and ctx["treinos_total"] == len(tr) > 10 and ctx["treinos_limitados"]
    datas = [t["data"] for t in ctx["treinos"]]
    assert datas[-1].endswith("26/08/2026")
    saida = R.renderizar_html(ctx)
    assert "10 treinos mais recentes" in saida and f"Total de treinos no período: {len(tr)}" in saida


def test_gramatica_da_frase_no_singular_e_plural():
    atleta, ev, pr = S.pkz_sintetico()
    um = [p for p in pr if p["data"] == "2026-08-26"]
    ctx = R.montar_contexto("PKZ", atleta, "semanal", S.REFERENCIA, evolucoes=[], presencas=um)
    frase = "".join(t for t, _ in ctx["hero"]["frase"])
    assert frase == "Atleta compareceu a 1 de 1 treino na semana"


# ------------------------------------------------------------------ geração do PDF
@pytest.fixture(scope="module")
def pdfs(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("pdfs-sinteticos")
    gerados = {}
    for unidade, periodo in SEIS:
        ctx = contexto(unidade, periodo)
        destino = pasta / ctx["template"].replace(".html", ".pdf")
        R.renderizar_pdf(ctx, destino)
        gerados[(unidade, periodo)] = destino
    return gerados


@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_gera_pdf_a4_valido_com_texto_e_fontes_embutidas(pdfs, unidade, periodo):
    leitor = PdfReader(str(pdfs[(unidade, periodo)]))
    assert len(leitor.pages) >= 1
    for pagina in leitor.pages:
        assert float(pagina.mediabox.width) == pytest.approx(595.3, abs=1)
        assert float(pagina.mediabox.height) == pytest.approx(841.9, abs=1)
    texto = "\n".join(p.extract_text() for p in leitor.pages)
    assert ("Atleta Exemplo" if unidade == "PKZ" else "Aluno Exemplo") in texto
    assert "Av. Armando Lombardi 949" in texto  # rodapé presente
    fontes = {str(f.get("/BaseFont")) for p in leitor.pages
              for f in (p["/Resources"].get("/Font") or {}).values() for f in [f.get_object()]}
    assert any("Inter" in f for f in fontes) and any("Barlow" in f for f in fontes), fontes


@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_paginacao_sem_paginas_vazias_e_rodape_so_no_fim(pdfs, unidade, periodo):
    paginas = [p.extract_text() for p in PdfReader(str(pdfs[(unidade, periodo)])).pages]
    assert all(len(t.strip()) > 80 for t in paginas)
    assert "Av. Armando Lombardi 949" in paginas[-1]
    assert all("Av. Armando Lombardi 949" not in t for t in paginas[:-1])
    assert "RELATÓRIO" in paginas[0].upper()
    assert all("RELATÓRIO DO" not in t.upper() and "RELATÓRIO DA" not in t.upper() for t in paginas[1:])


def test_pkz_mensal_e_anual_tem_mais_de_uma_pagina(pdfs):
    assert len(PdfReader(str(pdfs[("PKZ", "anual")])).pages) >= 2
    assert len(PdfReader(str(pdfs[("PKZ", "mensal")])).pages) >= 2


def test_fundos_coloridos_foram_renderizados(pdfs):
    import pymupdf
    pagina = pymupdf.open(str(pdfs[("PKZ", "mensal")]))[0]
    pixel = pagina.get_pixmap(dpi=40).pixel(30, 15)  # faixa do cabeçalho azul
    assert pixel[2] > pixel[0] + 40 and pixel[0] < 80, pixel


# ------------------------------------------------------- integração com a CLI/API
def test_gerar_relatorio_html_pkz_via_json(generator, sample_json_dir, tmp_path):
    destino = R.gerar_relatorio_html("PKZ", None, "mensal", date(2026, 8, 20), json_dir=sample_json_dir,
                                     saida_dir=tmp_path)
    assert destino.exists() and destino.name.startswith("relatorio_html_pkz_")
    assert len(PdfReader(str(destino)).pages) >= 1


def test_gerar_relatorio_html_one_to_one_usa_dados_da_api(generator, monkeypatch, tmp_path):
    atleta, pr, tr = S.o2o_sintetico()
    chamadas = {}

    def falso(atleta_id, inicio, fim):
        chamadas["args"] = (atleta_id, inicio, fim)
        return atleta, pr, tr

    monkeypatch.setattr(generator, "carregar_dados_one_to_one", falso)
    destino = R.gerar_relatorio_html("ONE_TO_ONE", S.O2O_ID, "semanal", S.REFERENCIA, saida_dir=tmp_path)
    assert chamadas["args"] == (S.O2O_ID, date(2026, 8, 24), date(2026, 8, 30))
    assert destino.exists()


def test_gerar_relatorio_html_sem_dados_nao_cria_pdf(generator, monkeypatch, tmp_path, capsys):
    atleta, _, _ = S.o2o_sintetico()
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *a: (atleta, [], []))
    assert R.gerar_relatorio_html("ONE_TO_ONE", S.O2O_ID, "mensal", S.REFERENCIA, saida_dir=tmp_path) is None
    assert list(tmp_path.iterdir()) == []
    assert "PDF não gerado" in capsys.readouterr().out


def test_cli_renderizador_html_chama_o_novo_gerador(generator, monkeypatch):
    chamado = {}
    monkeypatch.setattr(R, "gerar_relatorio_html", lambda *a, **k: chamado.setdefault("a", a))
    monkeypatch.setattr(sys, "argv", ["gerar_pdf.py", "abc", "--one-to-one", "--periodo", "anual",
                                      "--referencia", "2026-08-26", "--renderizador", "html"])
    generator.main()
    assert chamado["a"][:4] == ("ONE_TO_ONE", "abc", "anual", date(2026, 8, 26))


def test_cli_padrao_continua_sendo_reportlab(generator, monkeypatch):
    chamado = {}
    monkeypatch.setattr(generator, "gerar_relatorio", lambda *a, **k: chamado.setdefault("rl", a))
    monkeypatch.setattr(R, "gerar_relatorio_html", lambda *a, **k: pytest.fail("não deveria usar HTML"))
    monkeypatch.setattr(sys, "argv", ["gerar_pdf.py", "abc", "--periodo", "mensal", "--referencia", "2026-08-26"])
    generator.main()
    assert "rl" in chamado


def test_periodo_so_com_presenca_cancelada_nao_deixa_o_resumo_vazio():
    atleta, _, pr = S.pkz_sintetico()
    cancelada = [dict(p, status="cancelado") for p in pr if p["data"] == "2026-08-24"]
    ctx = R.montar_contexto("PKZ", atleta, "semanal", S.REFERENCIA, evolucoes=[], presencas=cancelada)
    assert "".join(t for t, _ in ctx["hero"]["frase"]) == "1 agendamento na semana, sem presença registrada"


# ------------------------------------------- rodapé no fim e blocos de apoio (gráficos)
@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_rodape_fica_no_fim_da_ultima_pagina(pdfs, unidade, periodo):
    import pymupdf
    ultima = pymupdf.open(str(pdfs[(unidade, periodo)]))[-1]
    fim_do_endereco = ultima.search_for("Armando")[0].y1
    # folha A4 = 842 pt, margem inferior de 12 mm (34 pt): o rodapé termina junto dela
    assert fim_do_endereco > 842 - 34 - 45, fim_do_endereco


@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_espaco_vazio_da_ultima_pagina_e_preenchido_com_blocos_de_apoio(pdfs, unidade, periodo):
    ctx = contexto(unidade, periodo)
    titulos = [e["titulo"] for e in ctx["extras"]]
    texto = " ".join(p.extract_text() for p in PdfReader(str(pdfs[(unidade, periodo)])).pages)
    assert any(t in texto for t in titulos), titulos


@pytest.mark.parametrize("unidade,periodo", SEIS)
def test_blocos_de_apoio_nao_aumentam_o_numero_de_paginas(unidade, periodo, tmp_path):
    ctx = contexto(unidade, periodo)
    base = tmp_path / "base.pdf"
    R.html_para_pdf(R.renderizar_html(ctx, incluir_extras=[]), base, ctx["largura"])
    final = R.renderizar_pdf(ctx, tmp_path / "final.pdf")
    assert len(PdfReader(str(final)).pages) == len(PdfReader(str(base)).pages)


def test_blocos_de_apoio_usam_apenas_dados_reais_do_periodo():
    ctx = contexto("PKZ", "mensal")
    extras = {e["id"]: e for e in ctx["extras"]}
    assert {"rosca", "variacao", "calendario", "dias_semana", "como_ler"} <= set(extras)
    rosca = str(extras["rosca"]["grafico"])
    assert ">13</text>" in rosca  # 9 presenças + 1 falta + 1 cancelada + 2 agendadas em agosto
    assert "Presenças" in rosca and "Faltas" in rosca
    # a variação desenhada é a mesma calculada para os testes
    assert "-4,3%" in str(extras["variacao"]["grafico"]) and "+4,5%" in str(extras["variacao"]["grafico"])


def test_one_to_one_extras_nao_trazem_dor_nem_dados_clinicos():
    for periodo in PERIODOS:
        ctx = contexto("ONE_TO_ONE", periodo)
        bruto = " ".join(str(e) for e in ctx["extras"])
        assert not re.search(r"\bdor\b|desconforto|lesão|queixa", bruto, flags=re.I)


def test_sem_dados_nao_cria_blocos_de_apoio_vazios():
    atleta, ev, _ = S.pkz_sintetico()
    ctx = R.montar_contexto("PKZ", atleta, "mensal", S.REFERENCIA, evolucoes=ev, presencas=[])
    ids = [e["id"] for e in ctx["extras"]]
    assert "rosca" not in ids and "calendario" not in ids and "dias_semana" not in ids
