"""Dashboard do atleta da PKZ: como ele evolui nos testes físicos.

Para rodar: streamlit run app.py (veja o README).
"""
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import dados

# Cores validadas para duas séries, inclusive para daltonismo.
AZUL, LARANJA = "#2a78d6", "#eb6834"
GRADE, EIXO, TINTA_FRACA, SUPERFICIE = "#e1e0d9", "#c3c2b7", "#52514e", "#ffffff"
LADOS = {"dir": "Direita", "esq": "Esquerda"}

SITUACOES = {
    "piorou": ("Piorou", "#fbebeb", "#a12424"),
    "melhorou": ("Melhorou", "#e5f4e4", "#006300"),
    "estavel": ("Estável", "#f0efec", "#52514e"),
    "sem_classificacao": ("Mudou, sem direção definida", None, None),
    "sem_comparacao": ("Primeira avaliação", None, None),
}
REAVALIACAO = {
    "vencida": ("Vencida", "red", ":material/error:"),
    "a_vencer": ("Vence em breve", "orange", ":material/schedule:"),
    "em_dia": ("Em dia", "green", ":material/check_circle:"),
}

st.set_page_config(page_title="Dashboard do atleta · PKZ", layout="wide")


# ---------------------------------------------------------------- formatação
def num(valor) -> str:
    texto = f"{float(valor):.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def com_unidade(valor, unidade) -> str:
    return "—" if valor is None else f"{num(valor)} {unidade}"


def data_br(iso: str | None) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "—"


def nome_do_teste(linha: dict) -> str:
    lado = LADOS.get(linha["lado"])
    return f"{linha['teste_nome']} · {lado.lower()}" if lado else linha["teste_nome"]


def prazo(dias: int) -> str:
    if dias < 0:
        return f"venceu há {-dias} {'dia' if dias == -1 else 'dias'}"
    if dias == 0:
        return "vence hoje"
    return f"vence em {dias} {'dia' if dias == 1 else 'dias'}"


def variacao(linha: dict) -> str:
    if linha["variacao_abs"] is None:
        return "—"
    absoluta = f"{float(linha['variacao_abs']):+.2f}".rstrip("0").rstrip(".").replace(".", ",")
    texto = f"{absoluta} {linha['unidade_medida']}"
    if linha["variacao_pct"] is not None:
        texto += f" ({float(linha['variacao_pct']):+.1f}%)".replace(".", ",")
    return texto


def a_confirmar(linha: dict) -> bool:
    """Classificação de um teste cuja regra a PKZ ainda não confirmou."""
    return not linha["confirmado"] and linha["situacao"] in ("melhorou", "piorou", "estavel")


def altura_da_tabela(linhas: int) -> int:
    """Altura para mostrar todas as linhas, sem rolagem dentro da tabela."""
    return (linhas + 1) * 35 + 3


def direcao(maior_melhor) -> str:
    return {True: "Maior é melhor", False: "Menor é melhor"}.get(maior_melhor, "Direção a definir")


# ---------------------------------------------------------------- leitura, com cache de 5 minutos
@st.cache_data(ttl=300, show_spinner="Lendo os atletas…")
def ler_atletas():
    return dados.atletas_pkz()


@st.cache_data(ttl=300, show_spinner="Lendo as reavaliações…")
def ler_reavaliacoes():
    return dados.reavaliacoes_pkz()


@st.cache_data(ttl=300, show_spinner="Lendo as avaliações do atleta…")
def ler_avaliacoes(atleta_id):
    return dados.evolucao(atleta_id), dados.comparacao(atleta_id)


# ---------------------------------------------------------------- blocos da tela do atleta
def bloco_reavaliacao(reavaliacao: dict | None) -> None:
    with st.container(border=True):
        st.markdown("**Reavaliação**")
        if not reavaliacao:
            st.write("Sem avaliação registrada.")
            return
        rotulo, cor, icone = REAVALIACAO[reavaliacao["situacao"]]
        st.badge(rotulo, icon=icone, color=cor)
        st.write(f"Data-limite {data_br(reavaliacao['vence_em'])}: {prazo(reavaliacao['dias_para_vencer'])}.")


def bloco_comparacao(linhas: list[dict]) -> None:
    st.subheader("Comparação com a avaliação anterior")
    if not linhas:
        st.info("Este atleta não tem testes para comparar.")
        return

    ordem = list(SITUACOES)
    linhas = sorted(linhas, key=lambda l: (ordem.index(l["situacao"]), nome_do_teste(l)))
    contagem = pd.Series([l["situacao"] for l in linhas]).value_counts()
    resumo = [f"{contagem[s]} {um if contagem[s] == 1 else varios}"
              for s, um, varios in (("melhorou", "melhorou", "melhoraram"), ("piorou", "piorou", "pioraram"),
                                    ("estavel", "estável", "estáveis")) if s in contagem]
    if resumo:
        st.write(" · ".join(resumo))

    tabela = pd.DataFrame([{
        "Teste": nome_do_teste(l),
        "Situação": SITUACOES[l["situacao"]][0] + (" *" if a_confirmar(l) else ""),
        "Anterior": (f"{com_unidade(l['valor_anterior'], l['unidade_medida'])} em {data_br(l['data_anterior'])}"
                     if l["data_anterior"] else "—"),
        "Atual": f"{com_unidade(l['valor_atual'], l['unidade_medida'])} em {data_br(l['data_atual'])}",
        "Variação": variacao(l),
    } for l in linhas])

    def colorir(texto: str) -> str:
        for rotulo, fundo, tinta in SITUACOES.values():
            if fundo and texto.startswith(rotulo):
                return f"background-color: {fundo}; color: {tinta}; font-weight: 600"
        return f"color: {TINTA_FRACA}"

    st.dataframe(
        tabela.style.map(colorir, subset=["Situação"]),
        hide_index=True,
        width="stretch",
        height=altura_da_tabela(len(tabela)),
        column_config={"Teste": st.column_config.TextColumn(width="large")},
    )
    if any(a_confirmar(l) for l in linhas):
        st.caption("\\* A PKZ ainda não confirmou a regra deste teste. Não use essa classificação "
                   "no relatório dos pais: lá, o teste não confirmado aparece só com os valores.")


def grafico(linhas: list[dict]) -> alt.LayerChart:
    tabela = pd.DataFrame([{
        "data": f"{l['data_avaliacao']}T12:00:00",  # com hora, para o fuso não voltar a data um dia
        "valor": float(l["valor"]),
        "lado": LADOS.get(l["lado"], "Resultado"),
        "Data": data_br(l["data_avaliacao"]),
        "Valor": com_unidade(l["valor"], l["unidade_medida"]),
        "rotulo": f"{LADOS[l['lado']][:3]}. {num(l['valor'])}" if l["lado"] else num(l["valor"]),
    } for l in linhas])
    tem_lados = any(l["lado"] for l in linhas)
    if tem_lados:
        cor = alt.Color("lado:N", title=None,
                        scale=alt.Scale(domain=list(LADOS.values()), range=[AZUL, LARANJA]),
                        legend=alt.Legend(orient="top", symbolType="circle"))
    else:
        cor = alt.value(AZUL)

    base = alt.Chart(tabela).encode(
        x=alt.X("data:T", title=None, scale=alt.Scale(padding=26),
                axis=alt.Axis(format="%d/%m/%y", grid=False, labelOverlap="greedy", tickCount=4,
                              domainColor=EIXO, tickColor=EIXO, labelColor=TINTA_FRACA)),
        y=alt.Y("valor:Q", title=linhas[0]["unidade_medida"], scale=alt.Scale(zero=False, padding=22),
                axis=alt.Axis(tickCount=4, domain=False, ticks=False, gridColor=GRADE, labelColor=TINTA_FRACA,
                              titleColor=TINTA_FRACA, titleFontWeight="normal",
                              labelExpr="replace(format(datum.value, '~g'), '.', ',')")),
        color=cor,
    )
    dicas = ["Data:N", "lado:N", "Valor:N"] if tem_lados else ["Data:N", "Valor:N"]
    ultimos = tabela[tabela["data"] == tabela["data"].max()].sort_values("valor", ascending=False)
    camadas = [
        base.mark_line(strokeWidth=2),
        base.mark_point(filled=True, size=70, opacity=1, stroke=SUPERFICIE, strokeWidth=2),
        base.mark_point(size=600, opacity=0).encode(tooltip=dicas),  # área maior para o mouse
    ]
    for posicao in range(len(ultimos)):  # o valor mais alto leva o rótulo por cima, o outro por baixo
        camadas.append(
            alt.Chart(ultimos.iloc[[posicao]])
            .mark_text(dy=-13 if posicao == 0 else 15, fontSize=12, fontWeight=600, color="#0F172A")
            .encode(x="data:T", y="valor:Q", text="rotulo:N")
        )
    return alt.layer(*camadas).properties(height=190).configure_view(stroke=None).configure_legend(
        labelColor=TINTA_FRACA, labelFontSize=12
    )


def bloco_evolucao(linhas: list[dict]) -> None:
    st.subheader("Evolução em cada teste")
    if not linhas:
        st.info("Este atleta ainda não tem medidas válidas nos testes.")
        return

    testes: dict[str, list[dict]] = {}
    for linha in linhas:
        testes.setdefault(linha["teste_nome"], []).append(linha)

    colunas = st.columns(2)
    for posicao, nome in enumerate(sorted(testes)):
        with colunas[posicao % 2].container(border=True):
            st.markdown(f"**{nome}**")
            st.caption(direcao(testes[nome][0]["maior_melhor"]))
            st.altair_chart(grafico(testes[nome]), theme=None, width="stretch")

    with st.expander("Ver os valores em tabela"):
        tabela = pd.DataFrame([{
            "Teste": nome_do_teste(l),
            "Data": l["data_avaliacao"],
            "Valor": com_unidade(l["valor"], l["unidade_medida"]),
        } for l in linhas])
        # aggfunc: duas avaliações no mesmo dia não derrubam a tabela; fica a última
        tabela = tabela.pivot_table(index="Teste", columns="Data", values="Valor", aggfunc="last").fillna("—")
        tabela.columns = [data_br(iso) for iso in tabela.columns]
        st.dataframe(tabela, width="stretch", height=altura_da_tabela(len(tabela)))


def tela_atleta(atletas: list[dict], reavaliacoes: list[dict]) -> None:
    incluir_inativos = st.toggle("Incluir atletas inativos", key="inativos_atleta")
    visiveis = [a for a in atletas if a["ativo"] or incluir_inativos]
    if not visiveis:
        st.info("Nenhum atleta ativo. Ligue a opção acima para ver os inativos.")
        return

    por_id = {a["atleta_id"]: a for a in visiveis}
    atleta_id = st.selectbox(
        "Atleta",
        list(por_id),
        format_func=lambda i: f"{por_id[i]['nome']} · {por_id[i]['categoria'] or 'sem categoria'}",
    )
    atleta = por_id[atleta_id]

    st.header(atleta["nome"])
    identificacao, situacao = st.columns([3, 2])
    with identificacao:
        for coluna, rotulo, valor in zip(st.columns(3), ("Categoria", "Última avaliação", "Avaliações"), (
            atleta["categoria"] or "Sem categoria",
            data_br(atleta["ultima_avaliacao_em"]),
            atleta["total_avaliacoes"],
        )):
            coluna.caption(rotulo)
            coluna.markdown(f"**{valor}**")
    with situacao:
        bloco_reavaliacao(next((r for r in reavaliacoes if r["atleta_id"] == atleta_id), None))

    if not atleta["total_avaliacoes"]:
        st.info("Este atleta ainda não fez nenhuma avaliação física.")
        return

    linhas_evolucao, linhas_comparacao = ler_avaliacoes(atleta_id)
    bloco_comparacao(linhas_comparacao)
    bloco_evolucao(linhas_evolucao)


def tela_reavaliacoes(atletas: list[dict], reavaliacoes: list[dict]) -> None:
    incluir_inativos = st.toggle("Incluir atletas inativos", key="inativos_lista")
    por_id = {a["atleta_id"]: a for a in atletas if a["ativo"] or incluir_inativos}
    linhas = [r for r in reavaliacoes if r["atleta_id"] in por_id]
    pendentes = [r for r in linhas if r["situacao"] != "em_dia"]

    vencidas, a_vencer, em_dia = st.columns(3)
    vencidas.metric("Vencidas", sum(r["situacao"] == "vencida" for r in linhas))
    a_vencer.metric("Vencem em breve", sum(r["situacao"] == "a_vencer" for r in linhas))
    em_dia.metric("Em dia", sum(r["situacao"] == "em_dia" for r in linhas))

    if not pendentes:
        st.success("Nenhuma reavaliação vencida ou a vencer.")
        return

    tabela = pd.DataFrame([{
        "Atleta": por_id[r["atleta_id"]]["nome"],
        "Categoria": por_id[r["atleta_id"]]["categoria"] or "Sem categoria",
        "Última avaliação": data_br(r["ultima_avaliacao_em"]),
        "Data-limite": data_br(r["vence_em"]),
        "Prazo": prazo(r["dias_para_vencer"]).capitalize(),
        "Situação": REAVALIACAO[r["situacao"]][0],
    } for r in pendentes])

    def colorir(texto: str) -> str:
        if texto == "Vencida":
            return "background-color: #fbebeb; color: #a12424; font-weight: 600"
        return "background-color: #f9eeda; color: #7a4d00; font-weight: 600"

    st.dataframe(tabela.style.map(colorir, subset=["Situação"]), hide_index=True, width="stretch",
                 height=altura_da_tabela(len(tabela)))


# ---------------------------------------------------------------- página
titulo, acao = st.columns([5, 1], vertical_alignment="bottom")
titulo.title("Dashboard do atleta · PKZ")
if acao.button("Atualizar dados", width="stretch"):
    st.cache_data.clear()

faltando = dados.variaveis_faltando()
if dados.usando_exemplos():
    st.warning("**Dados de exemplo, fictícios.** Para ler a API, preencha o arquivo .env (veja o README).")
elif faltando:
    st.error(f"Faltam variáveis no .env: {', '.join(faltando)}.")
    st.stop()

try:
    atletas = ler_atletas()
    reavaliacoes = ler_reavaliacoes()
    if not atletas:
        st.warning("A API não devolveu nenhum atleta da PKZ. Confira se o usuário do .env tem a unidade definida.")
        st.stop()
    aba_atleta, aba_reavaliacoes = st.tabs(["Atleta", "Reavaliações"])
    with aba_atleta:
        tela_atleta(atletas, reavaliacoes)
    with aba_reavaliacoes:
        tela_reavaliacoes(atletas, reavaliacoes)
except dados.ErroDados as erro:
    st.error(str(erro))
