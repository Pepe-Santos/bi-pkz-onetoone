"""Dashboards da PKZ e do One to One: atleta, comparativo e reavaliações, num app só.

Para rodar: streamlit run app.py (veja o README).
"""
import base64
import hashlib
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

import cartao
import comparativo
import dados
import graficos
import leitura
import relato

MARINHO = "#0e1a6b"
REAVALIACAO = {
    "vencida": ("Vencida", "#f5c77e", "#fbe9ec", "#9f1239"),
    "a_vencer": ("Vence em breve", "#c2f24a", "#fdeccb", "#7a4708"),
    "em_dia": ("Em dia", "#ffffff", "#dcf3e2", "#0d5132"),
}
TELA_ATLETA, TELA_COMPARATIVO, TELA_REAVALIACOES = "Atleta", "Comparativo", "Reavaliações"
TITULOS = {TELA_ATLETA: "Dashboard do atleta", TELA_COMPARATIVO: "Painel comparativo", TELA_REAVALIACOES: "Reavaliações"}
TODAS_AS_MODALIDADES = "Todas as modalidades"

ARQUIVO_LOGO = Path(__file__).resolve().parent.parent / "logo_pkz_one_to_one.png"
LOGO = base64.b64encode(ARQUIVO_LOGO.read_bytes()).decode()

st.set_page_config(page_title="Dashboards · PKZ & One to One", page_icon=str(ARQUIVO_LOGO), layout="wide")
st.html("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  .stApp, .stApp button, .stApp input, .stApp p, .stApp label, .stApp div { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
  .stApp [data-testid="stIconMaterial"], .stApp .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
  .stApp { background: #eef0f4; }
  .block-container { max-width: 1880px; padding: 0 clamp(1rem, 2.4vw, 3rem) 3rem; }
  [data-testid="stHeader"] { height: 0; background: transparent; }
  /* Aviso de desenvolvedor do Streamlit ("Help agents write better apps"): não é do produto. */
  [data-testid="stSkillsNudge"] { display: none !important; }
  /* Blocos que só carregam estilo ou script não ocupam lugar: sem eles, a barra do topo encosta no alto da tela. */
  [data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > :is(style, script):first-child):not(:has(> [data-testid="stHtml"] > :not(style, script))) { display: none; }

  /* Barra do topo, de ponta a ponta, igual à do painel comparativo */
  .st-key-topo { padding: 10px 0; background: #fff; box-shadow: 0 0 0 100vmax #fff; clip-path: inset(0 -100vmax); }
  .st-key-topo button { min-height: 44px; font-weight: 600; border-radius: 10px; }
  .st-key-tela button, .st-key-area button, .st-key-vista button { flex: 1 1 0; background: #f3f5fd; border-color: #dbe0f0; }
  .st-key-tela button p, .st-key-area button p, .st-key-vista button p { color: #12228e; font-weight: 600; font-size: 15px; }
  .st-key-tela button[aria-checked="true"], .st-key-tela button[aria-checked="true"]:hover,
  .st-key-area button[aria-checked="true"], .st-key-area button[aria-checked="true"]:hover,
  .st-key-vista button[aria-checked="true"], .st-key-vista button[aria-checked="true"]:hover { background: #12228e !important; border-color: #12228e !important; }
  .st-key-tela button[aria-checked="true"] p, .st-key-area button[aria-checked="true"] p, .st-key-vista button[aria-checked="true"] p { color: #fff !important; font-weight: 700; }
  .st-key-area button, .st-key-vista button { min-height: 40px; }

  /* Filtros, numa linha só */
  .st-key-filtros { padding: 12px clamp(14px, 1.2vw, 20px); border: 1px solid #dbe0f0; border-radius: 14px; background: #fff; }
  .st-key-filtros [data-testid="stWidgetLabel"] p { font-size: 13px; font-weight: 600; color: #475569; }
  .st-key-anterior button, .st-key-proximo button { min-height: 40px; padding: 0; }
  .st-key-anterior button p, .st-key-proximo button p { font-size: 22px; font-weight: 700; line-height: 1; }
  .st-key-inativos { padding-bottom: 8px; }
  .st-key-inativos p { font-size: 14px; font-weight: 500; color: #0f172a; }
  .stButton button { background: #fff; border-color: #12228e; color: #12228e; font-weight: 600; border-radius: 10px; }
  .stButton button:hover { background: #12228e; color: #fff; border-color: #12228e; }
  .st-key-botao_comparar button { min-height: 40px; background: #12228e; color: #fff; }
  .st-key-botao_comparar button p { color: #fff; font-weight: 700; }
  .st-key-botao_comparar button:disabled { background: #f3f5fd; border-color: #dbe0f0; }
  .st-key-botao_comparar button:disabled p { color: #94a3b8; }
  .st-key-comparar { padding: clamp(14px, 1.2vw, 20px); border: 1px solid #dbe0f0; border-radius: 14px; background: #fff; }

  /* Faixa azul de cada tela */
  .heroi { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 8fr); gap: 14px clamp(16px, 1.6vw, 28px); align-items: center; padding: clamp(15px, 1.2vw, 22px) clamp(18px, 1.5vw, 26px); border-radius: 14px; background: #0e1a6b; }
  .heroi-rotulo { font-size: clamp(10px, .75vw, 12.5px); font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #c2f24a; }
  .heroi-frase { margin: 6px 0 0; font-size: clamp(17px, 1.4vw, 25px); line-height: 1.3; font-weight: 700; color: #fff; }
  .heroi-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: clamp(8px, .7vw, 12px); }
  .heroi-tile { min-width: 0; padding: clamp(10px, .8vw, 14px) clamp(12px, .9vw, 16px); border: 1px solid rgba(255,255,255,.16); border-radius: 11px; background: rgba(255,255,255,.08); }
  .heroi-tile b { display: block; font-size: clamp(25px, 2vw, 36px); font-weight: 800; line-height: 1.05; }
  .heroi-tile b.texto { font-size: clamp(18px, 1.35vw, 24px); line-height: 1.25; }
  .heroi-tile span { display: block; margin-top: 5px; font-size: clamp(13px, .9vw, 15px); font-weight: 600; color: #fff; }
  .heroi-tile small { display: block; margin-top: 1px; font-size: clamp(11.5px, .78vw, 13px); line-height: 1.3; color: #c9d3e8; }

  /* Cartão, radar e descrição: colunas sempre da mesma altura */
  .linha-topo { display: grid; grid-template-columns: minmax(0, 4fr) minmax(0, 4fr) minmax(0, 5fr); gap: clamp(12px, 1vw, 18px); align-items: stretch; }
  @media (max-width: 1250px) { .linha-topo { grid-template-columns: repeat(2, minmax(0, 1fr)); } .linha-topo > :last-child { grid-column: 1 / -1; } }
  @media (max-width: 900px) { .linha-topo { grid-template-columns: minmax(0, 1fr); } .heroi { grid-template-columns: minmax(0, 1fr); } }
  @media (max-width: 640px) { .st-key-anterior, .st-key-proximo { display: none; } }

  [data-testid="stExpander"] details { border-color: #dbe0f0; border-radius: 14px; background: #fff; }
  [data-testid="stExpander"] summary p { font-weight: 600; color: #12228e; }
""" + graficos.CSS + comparativo.CSS + "</style>")


# Campos de escolha só aceitam escolher: nada de digitar, colar ou apagar o texto mostrado.
# Setas, Enter e clique continuam funcionando para escolher uma opção.
st.html("""<script>
(() => {
  if (window.__soEscolher) return;
  window.__soEscolher = true;
  const ehCampo = (alvo) => alvo instanceof HTMLInputElement && alvo.closest('[data-testid="stSelectbox"], [data-testid="stMultiSelect"]');
  for (const evento of ["beforeinput", "paste", "drop", "cut"]) {
    document.addEventListener(evento, (e) => { if (ehCampo(e.target)) e.preventDefault(); }, true);
  }
})();
</script>
<style>
  [data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input { caret-color: transparent; cursor: pointer; }
</style>""", unsafe_allow_javascript=True)


# ---------------------------------------------------------------- formatação
def data_br(iso: str | None) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "—"


def prazo(dias: int) -> str:
    if dias < 0:
        return f"venceu há {-dias} {'dia' if dias == -1 else 'dias'}"
    if dias == 0:
        return "vence hoje"
    return f"vence em {dias} {'dia' if dias == 1 else 'dias'}"


def prazo_da_reavaliacao(reavaliacao: dict | None) -> str | None:
    if not reavaliacao:
        return None
    return f"{prazo(reavaliacao['dias_para_vencer']).capitalize()}, em {data_br(reavaliacao['vence_em'])}."


def categoria_de(atleta: dict) -> str:
    return (atleta["categoria"] or "Sem categoria").replace("_", " ").capitalize()


def rotulo_do_atleta(atleta: dict) -> str:
    """Nome, idade e o que mais identifica o atleta. A idade vem antes da categoria: é ela que o filtro usa."""
    partes = [atleta["nome"] or "Sem nome", f"{atleta['idade']} anos" if atleta["idade"] is not None else "idade não informada"]
    if atleta["modalidade"]:
        partes.append(atleta["modalidade"])
    elif atleta["categoria"]:
        partes.append(categoria_de(atleta))
    n = atleta["total_avaliacoes"]
    partes.append(f"{n} {'avaliação' if n == 1 else 'avaliações'}")
    if not atleta["ativo"]:
        partes.append("inativo")
    return " · ".join(partes)


# ---------------------------------------------------------------- leitura, com cache de 5 minutos
@st.cache_data(ttl=300, show_spinner="Lendo os atletas…")
def ler_atletas():
    return dados.atletas_pkz()


@st.cache_data(ttl=300, show_spinner="Lendo as reavaliações…")
def ler_reavaliacoes():
    return dados.reavaliacoes_pkz()


@st.cache_data(ttl=300, show_spinner="Lendo as avaliações do atleta…")
def ler_avaliacoes(atleta_id):
    return dados.evolucao(atleta_id), dados.comparacao(atleta_id), dados.presenca(atleta_id), dados.treinos(atleta_id)


@st.cache_data(ttl=300, show_spinner="Lendo os atletas do login…")
def ler_atletas_do_login():
    return dados.atletas_do_login()


@st.cache_data(ttl=300, show_spinner="Lendo a chamada…")
def ler_presencas():
    return dados.presencas_do_login()


@st.cache_data(ttl=300, show_spinner=False)
def ler_unidade_do_login():
    return dados.unidade_do_login()


@st.cache_data(ttl=300, show_spinner="Lendo os resultados do grupo…")
def ler_medidas():
    return dados.medidas_do_grupo()


# ---------------------------------------------------------------- blocos em HTML
def faixa_superior(titulo: str) -> str:
    return f"""
<div style="display:flex;align-items:center;gap:12px">
  <img alt="PKZ One to One Studio" src="data:image/png;base64,{LOGO}" style="display:block;width:52px;height:52px;flex-shrink:0;border-radius:50%">
  <div style="min-width:0">
    <div style="font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#12228e">PKZ &amp; One to One</div>
    <div style="margin-top:1px;font-size:clamp(19px,1.5vw,24px);font-weight:700;line-height:1.15;color:#0f172a">{escape(titulo)}</div>
  </div>
</div>"""


tile, heroi = graficos.tile, graficos.heroi


def resumo_do_atleta(atleta, comparacao, presenca, reavaliacao, n_datas) -> str:
    presentes = sum(l["status"] == "presente" for l in presenca)
    faltas = sum(l["status"] == "falta" for l in presenca)
    chamadas = presentes + faltas
    tiles = [tile(atleta["total_avaliacoes"], "Avaliações",
                  f"última em {data_br(atleta['ultima_avaliacao_em'])}" if atleta["ultima_avaliacao_em"] else "nenhuma ainda")]
    if n_datas >= 2:
        tiles.append(tile(sum(l["situacao"] == "melhorou" for l in comparacao), "Melhoraram", "contra a avaliação anterior", "#c2f24a"))
        tiles.append(tile(sum(l["situacao"] == "piorou" for l in comparacao), "Pioraram", "contra a avaliação anterior", "#f5c77e"))
    else:
        tiles.append(tile("Sem comparação", "Evolução", "a partir da 2ª avaliação", "#f5c77e", em_texto=True))
    tiles.append(tile(f"{round(100 * presentes / chamadas)}%" if chamadas else "—", "Presença",
                      f"{chamadas} {'chamada registrada' if chamadas == 1 else 'chamadas registradas'}" if chamadas else "sem chamada registrada"))
    if reavaliacao:
        rotulo, cor, _, _ = REAVALIACAO[reavaliacao["situacao"]]
        tiles.append(tile(rotulo, "Reavaliação", f"{prazo(reavaliacao['dias_para_vencer'])}, {data_br(reavaliacao['vence_em'])}", cor, em_texto=True))
    if not atleta["total_avaliacoes"]:
        frase = "Este atleta ainda não fez nenhuma avaliação física."
    elif n_datas < 2:
        frase = "Só há 1 avaliação até agora: ainda não dá para comparar a evolução."
    else:
        frase = relato.frase_da_comparacao(comparacao) or "As duas últimas avaliações não têm testes em comum para comparar."
    return heroi("Visão geral", frase, tiles)


def tabela_html(cabecalhos, linhas, colunas_fixas="minmax(220px,1.6fr)") -> str:
    """Tabela com rolagem lateral só nela, para não quebrar a página no celular."""
    molde = f"{colunas_fixas} " + " ".join(["minmax(130px,1fr)"] * (len(cabecalhos) - 1))
    celula_topo = "padding:9px 14px;font-size:13.5px;font-weight:600;color:#475569;background:#f3f5fd"
    corpo = "".join(
        f'<div style="display:grid;grid-template-columns:{molde};align-items:center;border-top:1px solid #eef1f6">'
        + "".join(f'<div style="padding:7px 14px;font-size:14px;color:#0f172a">{c}</div>' for c in linha)
        + "</div>"
        for linha in linhas
    )
    return (
        '<div style="overflow-x:auto;border:1px solid #dbe0f0;border-radius:14px;background:#fff">'
        '<div style="min-width:760px">'
        f'<div style="display:grid;grid-template-columns:{molde}">'
        + "".join(f'<div style="{celula_topo}">{c}</div>' for c in cabecalhos)
        + f"</div>{corpo}</div></div>"
    )


def pilula(texto, fundo, tinta) -> str:
    return (f'<span style="display:inline-block;padding:3px 9px;border-radius:7px;background:{fundo};color:{tinta};'
            f'font-size:13.5px;font-weight:700">{escape(texto)}</span>')


def painel_radar(dados_do_cartao: dict) -> str:
    return ('<div class="painel">' + graficos.titulo_de_painel("Perfil do atleta", "Comparado com os colegas: quanto mais longe do centro, melhor.")
            + graficos.radar(dados_do_cartao) + "</div>")


def painel_destaques(perfil: list[dict], faixa: str, maximo: int = 3) -> str:
    return ('<div class="painel">' + graficos.titulo_de_painel("Onde se destaca", f"Posição entre os colegas de {faixa.lower()}, em cada teste.")
            + graficos.destaques(perfil, maximo) + "</div>")


def painel_mudancas(itens: list[dict]) -> str:
    nota = ('<div class="tst-rodape">Classificação provisória: a PKZ ainda não confirmou as regras desses testes.</div>'
            if any(not i["confirmado"] for i in itens) else "")
    return ('<div class="painel">' + graficos.titulo_de_painel("O que mudou", "Valor da avaliação anterior → valor da última.")
            + graficos.mudancas_em_lista(itens) + nota + "</div>")


def aviso_da_evolucao(linhas: list[dict]) -> str:
    datas = sorted({l["data_avaliacao"] for l in linhas})
    if len(datas) >= 2:
        return ""
    return graficos.aviso(
        "Sem dados suficientes para comparar a evolução.",
        f"Este atleta tem só 1 avaliação, em {data_br(datas[0])}. Os gráficos de evolução aparecem a partir da 2ª avaliação. "
        "Por enquanto, cada gráfico mostra o resultado ao lado da média dos colegas da mesma faixa de idade.")


# ---------------------------------------------------------------- filtros
def _chave_da_lista(prefixo: str, ids: list[str]) -> str:
    """O Streamlit mantém na tela o valor antigo quando as opções de um campo mudam. Um campo por lista evita isso."""
    return f"{prefixo}_{hashlib.md5('|'.join(ids).encode()).hexdigest()[:10]}"


def _passar_atleta(ids: list[str], passo: int) -> None:
    atual = st.session_state.get("atleta_escolhido")
    posicao = ids.index(atual) if atual in ids else 0
    st.session_state["atleta_escolhido"] = ids[(posicao + passo) % len(ids)]


def _guardar(origem: str, destino: str) -> None:
    st.session_state[destino] = st.session_state[origem]


TODAS_AS_IDADES = "Todas as idades"
FAIXAS = [TODAS_AS_IDADES, *[f["nome"] for f in cartao.CATALOGO["faixas_de_idade"]]]
SEM_IDADE = "Idade não informada"
# Campos de escolha: só se seleciona, não se digita (o Streamlit deixa digitar para buscar, por padrão).
SO_ESCOLHER = {"filter_mode": None}


def _faixa_do_atleta(atleta: dict) -> str:
    return SEM_IDADE if atleta["idade"] is None else cartao.faixa_de_idade(atleta["idade"])


def _rotulo_da_faixa(faixa: str, atletas: list[dict]) -> str:
    """O nome da faixa e as idades que existem nela, para ninguém precisar adivinhar quem entra."""
    if faixa == TODAS_AS_IDADES:
        idades = [a["idade"] for a in atletas if a["idade"] is not None]
        return f"{faixa} ({min(idades)} a {max(idades)})" if idades else faixa
    idades = sorted({a["idade"] for a in atletas if a["idade"] is not None and _faixa_do_atleta(a) == faixa})
    if not idades:
        return f"{faixa} (nenhum nesta modalidade)"
    return f"{faixa} ({idades[0]} anos)" if len(idades) == 1 else f"{faixa} ({idades[0]} a {idades[-1]})"


def _contar(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def filtros_do_grupo(todos: list[dict]) -> tuple | None:
    """Área, modalidade, faixa de idade e inativos: a mesma linha nas telas Atleta e Comparativo.

    As chaves são as mesmas nas duas telas, então o que se escolhe numa continua escolhido na outra.
    Devolve (área, modalidade, faixa, atletas da área, atletas filtrados, nota sobre a modalidade).
    """
    areas = {"TODAS": [comparativo.PKZ, comparativo.ONE_TO_ONE], "PKZ": [comparativo.PKZ],
             "ONE_TO_ONE": [comparativo.ONE_TO_ONE]}.get(ler_unidade_do_login(), [])
    if not areas:
        st.warning("Este login ainda não tem unidade definida. Fale com o Desenvolvimento.")
        return None
    if st.session_state.get("area") not in areas:
        st.session_state.pop("area", None)
    st.session_state.setdefault("area", areas[0])

    c_area, c_mod, c_faixa, c_inativos = st.columns([1.7, 2.4, 2.2, 1.5], vertical_alignment="bottom", gap="small")
    area = c_area.segmented_control("Área", areas, required=True, key="area", width="stretch", disabled=len(areas) == 1,
                                    help="Cada login vê só a própria unidade." if len(areas) == 1 else None)
    da_area = [a for a in todos if (a["unidade"] == "PKZ") == (area == comparativo.PKZ)]
    n_inativos = sum(not a["ativo"] for a in da_area)
    inativos = c_inativos.toggle(f"Incluir inativos ({n_inativos})", key="inativos", disabled=not n_inativos,
                                 help=(f"{_contar(n_inativos, 'aluno inativo', 'alunos inativos')} nesta área. "
                                       "Ligado, eles entram na lista, nos cartões e nas médias." if n_inativos
                                       else "Nenhum aluno inativo nesta área."))
    ativos = [a for a in da_area if a["ativo"] or inativos]
    nota = ""
    if area == comparativo.PKZ:
        # Só modalidades com atletas: nenhuma opção leva a uma lista vazia.
        existentes = {a["modalidade"] for a in ativos if a["modalidade"]}
        opcoes = [TODAS_AS_MODALIDADES, *[m for m in cartao.MODALIDADES_PKZ if m in existentes],
                  *sorted(existentes - set(cartao.MODALIDADES_PKZ))]
        if st.session_state.get("modalidade") not in opcoes:
            st.session_state.pop("modalidade", None)
        por_modalidade = {m: sum(a["modalidade"] == m for a in ativos) for m in opcoes[1:]}
        modalidade = c_mod.selectbox("Modalidade", opcoes, key="modalidade", **SO_ESCOLHER,
                                     format_func=lambda m: m if m == TODAS_AS_MODALIDADES else f"{m} ({por_modalidade[m]})",
                                     help="Entre parênteses, quantos atletas há na modalidade. Todos os atletas de uma modalidade têm os mesmos atributos.")
        com_modalidade = sum(bool(a["modalidade"]) for a in ativos)
        if com_modalidade < len(ativos):
            nota = (f'<div class="tst-rodape">Modalidade registrada em {com_modalidade} de {len(ativos)} atletas. '
                    "Os outros aparecem só em Todas as modalidades, com os atributos gerais.</div>")
    else:
        modalidade = TODAS_AS_MODALIDADES
        c_mod.selectbox("Modalidade", ["Sem modalidade no One to One"], key="modalidade_oto", disabled=True, **SO_ESCOLHER)
    # As faixas saem das idades cadastradas na área: toda idade tem onde cair e nenhuma faixa aparece sem aluno.
    da_modalidade = [a for a in ativos if modalidade == TODAS_AS_MODALIDADES or a["modalidade"] == modalidade]
    presentes = {_faixa_do_atleta(a) for a in ativos}
    faixas = [TODAS_AS_IDADES, *[f for f in FAIXAS[1:] if f in presentes], *([SEM_IDADE] if SEM_IDADE in presentes else [])]
    if st.session_state.get("faixa") not in faixas:
        st.session_state.pop("faixa", None)
    faixa = c_faixa.selectbox("Faixa de idade", faixas, key="faixa", **SO_ESCOLHER,
                              format_func=lambda f: _rotulo_da_faixa(f, da_modalidade),
                              help="Entre parênteses, as idades que existem na faixa. A comparação dos atributos é sempre com a mesma faixa.")
    lista = [a for a in da_modalidade if faixa == TODAS_AS_IDADES or _faixa_do_atleta(a) == faixa]
    return area, modalidade, faixa, ativos, lista, nota


def barra_de_filtros(todos: list[dict]) -> dict | None:
    """A barra comum e, embaixo, o atleta, com setas para passar de um para o outro."""
    with st.container(key="filtros"):
        grupo = filtros_do_grupo(todos)
        if grupo is None:
            return None
        area, modalidade, faixa, _, lista, nota = grupo
        por_id = {a["atleta_id"]: a for a in lista}
        ids = list(por_id)
        if ids and st.session_state.get("atleta_escolhido") not in ids:
            st.session_state["atleta_escolhido"] = ids[0]

        anterior, escolha, proximo = st.columns([.32, 7.4, .32], vertical_alignment="bottom", gap="small")
        anterior.button("‹", key="anterior", on_click=_passar_atleta, args=(ids, -1), width="stretch", disabled=not ids)
        if ids:
            chave = _chave_da_lista("atleta", ids)
            st.session_state[chave] = st.session_state["atleta_escolhido"]
            atleta_id = escolha.selectbox(
                f"Atleta · {len(ids)} na lista", ids, key=chave, on_change=_guardar,
                args=(chave, "atleta_escolhido"), **SO_ESCOLHER, format_func=lambda i: rotulo_do_atleta(por_id[i]),
            )
        else:
            escolha.selectbox("Atleta", ["Nenhum atleta com esses filtros"], key="atleta_vazio", disabled=True, **SO_ESCOLHER)
        proximo.button("›", key="proximo", on_click=_passar_atleta, args=(ids, 1), width="stretch", disabled=not ids)
        if nota:
            st.html(nota)

    if not ids:
        if modalidade != TODAS_AS_MODALIDADES:
            st.html(graficos.aviso(f"Nenhum atleta com a modalidade {modalidade} registrada{'' if faixa == TODAS_AS_IDADES else ' nesta faixa de idade'}.",
                                   "Escolha Todas as modalidades, ou peça para registrar a modalidade dos atletas."))
        elif faixa != TODAS_AS_IDADES:
            st.html(graficos.aviso(f"Nenhum atleta de {faixa.lower()} nesta área.", "Escolha outra faixa de idade."))
        else:
            st.html(graficos.aviso("Nenhum atleta ativo.", "Ligue a opção Incluir inativos para ver os outros."))
        return None
    return por_id[atleta_id]


# ---------------------------------------------------------------- telas
def tela_atleta(todos: list[dict], reavaliacoes: list[dict]) -> None:
    atleta = barra_de_filtros(todos)
    if atleta is None:
        return
    atleta_id = atleta["atleta_id"]
    one_to_one = atleta["unidade"] == "ONE_TO_ONE"
    da_unidade = [a for a in todos if a["unidade"] == atleta["unidade"]]

    medidas = ler_medidas()
    # Presença e relatórios de treino existem mesmo sem avaliação física (é o caso do One to One).
    linhas_evolucao, linhas_comparacao, linhas_presenca, linhas_treinos = ler_avaliacoes(atleta_id)
    reavaliacao = next((r for r in reavaliacoes if r["atleta_id"] == atleta_id), None)
    faixa = cartao.faixa_de_idade(atleta["idade"])
    ids_do_grupo = [a["atleta_id"] for a in da_unidade if a["idade"] is not None and cartao.faixa_de_idade(a["idade"]) == faixa]
    ultimos = cartao.ultimos_valores(medidas)
    perfil = leitura.perfil_do_atleta(linhas_evolucao, ids_do_grupo, ultimos)
    n_datas = len({l["data_avaliacao"] for l in linhas_evolucao})
    dados_do_cartao = cartao.calcular_cartoes(da_unidade, medidas, atleta["modalidade"], one_to_one=one_to_one)[atleta_id]

    # 1. Como o atleta está
    st.html(resumo_do_atleta(atleta, linhas_comparacao, linhas_presenca, reavaliacao, n_datas))
    st.html('<div class="linha-topo">'
            + cartao.html_do_cartao(atleta, dados_do_cartao)
            + painel_radar(dados_do_cartao)
            + relato.html_do_relato(atleta, linhas_evolucao, linhas_comparacao, linhas_presenca, linhas_treinos, perfil, prazo_da_reavaliacao(reavaliacao))
            + "</div>")

    if not linhas_evolucao:
        st.html(graficos.aviso("Sem dados para comparar.", "Os gráficos aparecem depois da primeira avaliação física deste aluno."))
        return

    # 2. Onde está forte e o que mudou
    itens = leitura.mudancas(linhas_comparacao)
    st.html(f'<div class="dupla">{painel_destaques(perfil, faixa, 5)}{painel_mudancas(itens)}</div>' if itens else painel_destaques(perfil, faixa))

    # 3. Como veio evoluindo
    st.html('<div class="painel-titulo" style="margin-top:6px">Como veio evoluindo</div>'
            + (f'<div style="margin-top:9px">{aviso_da_evolucao(linhas_evolucao)}</div>' if n_datas < 2 else ""))
    st.html(graficos.painel_de_evolucao(linhas_evolucao, ids_do_grupo, ultimos, one_to_one=one_to_one))
    with st.expander("Ver todos os valores em tabela"):
        st.html(graficos.tabela_de_valores(linhas_evolucao, linhas_comparacao))


def _cartoes_de(atletas_pkz: list[dict], atletas_oto: list[dict], medidas: list[dict]) -> dict:
    """Cada atleta da PKZ nos atributos da própria modalidade; o One to One, no conjunto dele."""
    cartoes = {}
    for modalidade in {a["modalidade"] for a in atletas_pkz}:
        calculados = cartao.calcular_cartoes(atletas_pkz, medidas, modalidade)
        cartoes.update({a["atleta_id"]: calculados[a["atleta_id"]] for a in atletas_pkz if a["modalidade"] == modalidade})
    if atletas_oto:
        cartoes.update(cartao.calcular_cartoes(atletas_oto, medidas, None, one_to_one=True))
    return cartoes


VAZIO = ""


def _limpar_comparacao() -> None:
    st.session_state.pop("comparacao_feita", None)


def comparar_dois(lista: list[dict], cartoes: dict, area: str) -> None:
    """1º atleta, 2º atleta da mesma modalidade, botão Comparar e, depois do clique, o gráfico dos dois."""
    por_id = {a["atleta_id"]: a for a in lista}
    rotulo = lambda i: "Escolha um atleta" if i == VAZIO else rotulo_do_atleta(por_id[i])
    with st.container(key="comparar"):
        st.html(graficos.titulo_de_painel("Comparar dois atletas",
                                          "Escolha o primeiro, depois o segundo, da mesma modalidade, e clique em Comparar."))
        c1, c2, c_botao = st.columns([3, 3, 1.2], vertical_alignment="bottom", gap="small")
        ids = list(por_id)
        if st.session_state.get("comparar_1") not in [VAZIO, *ids]:
            st.session_state.pop("comparar_1", None)
        primeiro = c1.selectbox("1º atleta", [VAZIO, *ids], key="comparar_1", format_func=rotulo,
                                on_change=_limpar_comparacao, **SO_ESCOLHER)
        # O segundo só pode ser da mesma modalidade do primeiro: assim os atributos são os mesmos para os dois.
        mesma = [i for i in ids if i != primeiro and (area != comparativo.PKZ or not primeiro
                                                      or por_id[i]["modalidade"] == por_id[primeiro]["modalidade"])]
        if st.session_state.get("comparar_2") not in [VAZIO, *mesma]:
            st.session_state.pop("comparar_2", None)
        segundo = c2.selectbox("2º atleta" + (f" · {por_id[primeiro]['modalidade']}" if primeiro and por_id[primeiro]["modalidade"] else ""),
                               [VAZIO, *mesma], key="comparar_2", format_func=rotulo, disabled=not primeiro,
                               on_change=_limpar_comparacao, **SO_ESCOLHER)
        if c_botao.button("Comparar", key="botao_comparar", width="stretch", type="primary", disabled=not (primeiro and segundo)):
            st.session_state["comparacao_feita"] = (primeiro, segundo)
        if primeiro and not mesma:
            st.html(graficos.aviso("Não há outro atleta desta modalidade com esses filtros.",
                                   "Amplie a faixa de idade ou ligue Incluir inativos para ter com quem comparar."))
    feita = st.session_state.get("comparacao_feita")
    if feita and feita == (primeiro, segundo) and all(i in por_id for i in feita):
        a, b = (por_id[i] for i in feita)
        st.html(comparativo.comparacao(a, b, cartoes[a["atleta_id"]], cartoes[b["atleta_id"]], [cartoes[x["atleta_id"]] for x in lista]))


def tela_comparativo() -> None:
    todos = [{**a, "modalidade": cartao.nome_da_modalidade(a["modalidade"])} for a in ler_atletas_do_login()]
    with st.container(key="filtros"):
        grupo = filtros_do_grupo(todos)
        if grupo is None:
            return
        area, modalidade, faixa, ativos, lista, nota = grupo
        pkz = [a for a in todos if a["unidade"] == "PKZ"]
        oto = [a for a in todos if a["unidade"] == "ONE_TO_ONE"]
        cartoes = _cartoes_de(pkz, oto, ler_medidas())

        definicoes = (cartao.CATALOGO["modalidades"]["PKZ"].get(modalidade)
                      if area == comparativo.PKZ and modalidade != TODAS_AS_MODALIDADES else None)
        if definicoes is None and area == comparativo.PKZ and modalidade not in (TODAS_AS_MODALIDADES, *cartao.MODALIDADES_PKZ):
            definicoes = cartao.CATALOGO["modalidades"]["GERAL"]
        chaves = {"Nota provisória": comparativo.NOTA} | ({d["nome"]: d["sigla"] for d in definicoes} if definicoes else {})
        if st.session_state.get("comparar_por") not in chaves:
            st.session_state.pop("comparar_por", None)
        st.session_state.setdefault("vista", "Cards")
        c_chave, c_vista, _ = st.columns([2.4, 1.7, 3.3], vertical_alignment="bottom", gap="small")
        if area == comparativo.ONE_TO_ONE:
            chaves |= {d["nome"]: d["sigla"] for d in cartao.CATALOGO["modalidades"]["ONE_TO_ONE"]["Todas"] if d["tipo"] != "sem_dados"}
        if st.session_state.get("comparar_por") not in chaves:
            st.session_state.pop("comparar_por", None)
        nome_da_chave = c_chave.selectbox("Comparar por", list(chaves), key="comparar_por", disabled=len(chaves) == 1, **SO_ESCOLHER,
                                          help=None if len(chaves) > 1 else "Para comparar por um atributo, escolha uma modalidade.")
        vista = c_vista.segmented_control("Ver como", ["Cards", "Ranking"], required=True, key="vista", width="stretch")
        if nota:
            st.html(nota)
    chave = chaves[nome_da_chave]

    presencas_por_atleta: dict[str, list[dict]] = {}
    for p in ler_presencas():
        presencas_por_atleta.setdefault(p["atleta_id"], []).append(p)
    hoje = comparativo.hoje_em_sao_paulo()

    st.html(comparativo.heroi(nome_da_chave, lista, cartoes, chave, area))
    if not lista:
        st.html(graficos.aviso("Nenhum atleta com esses filtros.", "Amplie a faixa de idade ou escolha Todas as modalidades."))
        return
    st.html('<div class="dupla">' + comparativo.resumo_do_dia(lista, presencas_por_atleta, hoje)
            + comparativo.distribuicao(lista, cartoes) + "</div>")

    if len(lista) >= 2:
        comparar_dois(lista, cartoes, area)

    ordenados = comparativo.ordenar(lista, cartoes, chave)
    recorte = modalidade if area == comparativo.PKZ else comparativo.ONE_TO_ONE
    st.html(f'<div class="titulo-lista"><div class="painel-titulo">{escape(recorte)} · ordenados por {escape(nome_da_chave.lower())}</div>'
            f'<div class="tst-rodape">{len(lista)} {"atleta" if len(lista) == 1 else "atletas"}</div></div>')
    if vista == "Ranking":
        st.html(comparativo.ranking(ordenados, cartoes, chave, nome_da_chave))
    else:
        st.html(comparativo.grade_de_cartoes(ordenados, cartoes, chave, nome_da_chave, presencas_por_atleta, hoje))
    st.html(f'<div class="tst-rodape">{"Dados fictícios, só para teste." if dados.usando_exemplos() else "Dados reais, lidos da API, só para leitura."} Cada atributo é o percentil do atleta entre os da '
            'mesma faixa de idade; até 5 pontos de diferença conta como na média. A nota é provisória: a fórmula definitiva é da escola.</div>')


def tela_reavaliacoes(atletas: list[dict], reavaliacoes: list[dict]) -> None:
    with st.container(key="filtros"):
        st.toggle("Incluir atletas inativos", key="inativos")
    por_id = {a["atleta_id"]: a for a in atletas if a["ativo"] or st.session_state.get("inativos", False)}
    linhas = [r for r in reavaliacoes if r["atleta_id"] in por_id]
    pendentes = [r for r in linhas if r["situacao"] != "em_dia"]
    vencidas = sum(r["situacao"] == "vencida" for r in linhas)
    a_vencer = sum(r["situacao"] == "a_vencer" for r in linhas)
    em_dia = sum(r["situacao"] == "em_dia" for r in linhas)

    st.html(heroi(
        "Reavaliações", f"{vencidas} vencidas e {a_vencer} a vencer, de {len(linhas)} atletas avaliados.",
        [tile(vencidas, "Vencidas", "precisam de nova avaliação", "#f5c77e"),
         tile(a_vencer, "Vencem em breve", "nos próximos 30 dias", "#c2f24a"),
         tile(em_dia, "Em dia", "regra provisória de 90 dias")],
    ))
    if not pendentes:
        st.success("Nenhuma reavaliação vencida ou a vencer.")
        return
    tabela = []
    for r in pendentes:
        atleta = por_id[r["atleta_id"]]
        rotulo, _, fundo, tinta = REAVALIACAO[r["situacao"]]
        tabela.append([f'<strong class="cartao-nome" style="font-weight:600">{escape(atleta["nome"])}</strong>',
                       pilula(rotulo, fundo, tinta), escape(categoria_de(atleta)),
                       data_br(r["ultima_avaliacao_em"]), data_br(r["vence_em"]),
                       prazo(r["dias_para_vencer"]).capitalize()])
    st.html(tabela_html(["Atleta", "Situação", "Categoria", "Última avaliação", "Data-limite", "Prazo"], tabela))


# ---------------------------------------------------------------- página
# O Streamlit esquece um filtro quando a tela dele sai de cena: isto guarda a escolha ao trocar de tela.
for chave in ("modalidade", "inativos", "area", "faixa", "comparar_por", "vista"):
    if chave in st.session_state:
        st.session_state[chave] = st.session_state[chave]

with st.container(key="topo"):
    titulo, navegacao, acao = st.columns([4.2, 3.9, 1.1], vertical_alignment="center", gap="small")
    lugar_do_titulo = titulo.empty()
    tela = navegacao.segmented_control("Tela", [TELA_ATLETA, TELA_COMPARATIVO, TELA_REAVALIACOES], default=TELA_ATLETA, required=True,
                                       key="tela", label_visibility="collapsed", width="stretch")
    lugar_do_titulo.html(faixa_superior(TITULOS[tela]))
    if acao.button("Atualizar", width="stretch"):
        st.cache_data.clear()

faltando = dados.variaveis_faltando()
if dados.usando_exemplos():
    if not dados.DADOS_FICTICIOS:  # no modo apresentação, quem explica é o apresentador
        st.warning("**Dados de exemplo, fictícios.** Para ler a API, preencha o arquivo .env (veja o README).")
elif faltando:
    st.error(f"Faltam variáveis no .env: {', '.join(faltando)}.")
    st.stop()

try:
    if tela == TELA_COMPARATIVO:
        tela_comparativo()
        st.stop()
    if tela == TELA_ATLETA:
        tela_atleta([{**a, "modalidade": cartao.nome_da_modalidade(a["modalidade"])} for a in ler_atletas_do_login()],
                    ler_reavaliacoes())
        st.stop()
    atletas = [{**a, "modalidade": cartao.nome_da_modalidade(a["modalidade"])} for a in ler_atletas()]
    reavaliacoes = ler_reavaliacoes()
    if not atletas:
        st.warning("A API não devolveu nenhum atleta da PKZ. Confira se o usuário do .env tem a unidade definida.")
        st.stop()
    tela_reavaliacoes(atletas, reavaliacoes)
except dados.ErroDados as erro:
    st.error(str(erro))
