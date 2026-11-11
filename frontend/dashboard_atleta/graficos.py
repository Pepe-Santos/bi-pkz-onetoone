"""Cada dado na forma que comunica melhor. A análise está em ../ANALISE_GRAFICOS.md.

Todo teste tem o seu gráfico, em qualquer situação:
- 1 avaliação: duas barras, o atleta e a média do grupo. Não há evolução para mostrar, e a tela avisa.
- 2 avaliações: duas colunas, "antes e agora".
- 3 ou mais: linha com o valor escrito em cada avaliação.
- Saltos, por serem da mesma unidade: colunas lado a lado por tipo de salto.
- Pernas: direita e esquerda lado a lado, mais a diferença entre elas.
- Teste ainda não feito: o cartão continua lá, com o aviso.

Os gráficos são HTML e CSS: o texto fica sempre do mesmo tamanho, em qualquer largura de tela.
"""
import base64
import math
from datetime import date
from html import escape

import leitura

AZUL, VERDE, MARINHO = "#2343c8", "#2e9e5b", "#0e1a6b"
AZUL_CLARO, CINZA_GRUPO = "#b9c5ee", "#a7b0c4"
TINTA, TINTA_FRACA = "#0f172a", "#475569"
LADOS = {"dir": "Direita", "esq": "Esquerda"}
ASSIMETRIA_LIMITE = 10  # regra provisória do projeto
MAXIMO_DE_DATAS = 4  # em colunas agrupadas; mais que isso não cabe com o valor escrito

TESTES_DE_SALTO = ("saltos_vert_countermovement", "saltos_vert_squat_jump", "saltos_vert_abalakov")
NOMES_DE_SALTO = {"saltos_vert_countermovement": "Contramovimento", "saltos_vert_squat_jump": "Squat jump",
                  "saltos_vert_abalakov": "Abalakov"}
TESTES_DE_LADO = ("single_hop", "cross_hop")
NOMES_DE_TESTE = {
    "sprint_10": "Sprint 10 m", "sprint_20": "Sprint 20 m", "illinois": "Agilidade (Illinois)",
    "slalom_wallball": "Slalom com bola / Wall Ball", "single_hop": "Single hop (salto horizontal)", "cross_hop": "Cross hop",
    "banco_wells": "Banco de Wells (flexibilidade)", "estabilidade_aquabag": "Estabilidade Aquabag",
    "teste_vo2_distancia_total": "VO2 (distância)", "teste_vo2_vel_max": "VO2 (velocidade máxima)",
    "teste_vo2_tempo_total": "VO2 (tempo total)", "teste_vo2_tempo_vel_max": "VO2 (tempo na velocidade máxima)",
    "blazepod_vel_reacao_ms": "Blazepod (reação, tempo)", "blazepod_vel_reacao_hits": "Blazepod (reação, acertos)",
    "blazepod_foco": "Blazepod (foco)", "antropometria_altura": "Altura", "antropometria_peso": "Peso",
    "cadeira_isometrica": "Cadeira isométrica (força de inferiores)", "flexao_bracos": "Flexão de braços em 1 min",
    "prancha_ventral": "Prancha ventral (core)",
}
# (nome do grupo, largura na página, colunas, testes). "saltos" é o cartão único dos três saltos.
GRUPOS = (
    ("Velocidade e agilidade", "inteiro", 4, ("sprint_10", "sprint_20", "illinois", "slalom_wallball")),
    ("Salto e potência", "inteiro", 4, ("saltos", "single_hop", "cross_hop")),
    ("Resistência", "inteiro", 4, ("teste_vo2_distancia_total", "teste_vo2_vel_max", "teste_vo2_tempo_total", "teste_vo2_tempo_vel_max")),
    ("Flexibilidade e equilíbrio", "metade", 2, ("banco_wells", "estabilidade_aquabag")),
    ("Medidas do corpo", "metade", 2, ("antropometria_altura", "antropometria_peso")),
    ("Reação e foco", "inteiro", 3, ("blazepod_vel_reacao_ms", "blazepod_vel_reacao_hits", "blazepod_foco")),
)
# One to One: a ficha de avaliação da AP1 (força, core, potência, resistência e mobilidade).
GRUPOS_ONE_TO_ONE = (
    ("Força e core", "inteiro", 3, ("cadeira_isometrica", "flexao_bracos", "prancha_ventral")),
    ("Potência e resistência", "inteiro", 3, ("saltos_vert_countermovement", "teste_vo2_distancia_total")),
    ("Mobilidade", "metade", 2, ("banco_wells",)),
    ("Medidas do corpo", "metade", 2, ("antropometria_altura", "antropometria_peso")),
)
ORDEM_DOS_TESTES = [t for grupo in GRUPOS + GRUPOS_ONE_TO_ONE for chave in grupo[3] for t in (TESTES_DE_SALTO if chave == "saltos" else (chave,))]

# Vai uma vez só na página, pelo app.py.
CSS = """
  .aviso { display:flex; gap:11px; align-items:flex-start; padding:12px 15px; border:1px solid #f0d9a4; border-radius:12px; background:#fdf3dc; color:#6b3f06; font-size:14.5px; line-height:1.45; }
  .aviso strong { font-weight:700; }
  .aviso-marca { display:grid; place-items:center; flex-shrink:0; width:22px; height:22px; border-radius:50%; background:#b97a12; color:#fff; font-size:13px; font-weight:800; }
  .painel { display:flex; flex-direction:column; gap:10px; height:100%; min-width:0; padding:clamp(15px,1.2vw,22px) clamp(16px,1.3vw,24px); border:1px solid #dbe0f0; border-radius:14px; background:#fff; }
  .painel-titulo { font-size:clamp(18px,1.3vw,23px); font-weight:800; letter-spacing:-.01em; color:#12228e; }
  .painel-sub { margin-top:2px; font-size:clamp(13px,.9vw,15px); line-height:1.4; color:#475569; }
  .grupos { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px 14px; }
  .grupo { min-width:0; }
  .grupo.inteiro { grid-column:1 / -1; }
  .grupo-nome { margin-bottom:8px; font-size:clamp(11.5px,.8vw,13.5px); font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#4d6b0f; }
  .cartoes { display:grid; gap:14px; }
  .cartoes.c4 { grid-template-columns:repeat(4,minmax(0,1fr)); }
  .cartoes.c3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .cartoes.c2 { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .largo { grid-column:span 2; }
  .tst { display:flex; flex-direction:column; gap:7px; height:100%; min-width:0; padding:14px 16px; border:1px solid #dbe0f0; border-radius:14px; background:#fff; }
  .tst-nome { font-size:14.5px; font-weight:700; line-height:1.25; color:#0f172a; }
  .tst-dica { margin-top:1px; font-size:12.5px; color:#64748b; }
  .tst-valor { font-size:clamp(25px,1.9vw,33px); font-weight:800; line-height:1.1; color:#12228e; }
  .tst-valor small { font-size:14px; font-weight:600; color:#64748b; }
  .tst-grafico { margin-top:auto; padding-top:6px; }
  .tst-rodape { font-size:12.5px; line-height:1.35; color:#475569; }
  .tst.vazio { align-items:flex-start; border:1px dashed #e0c58b; background:#fffbf2; }
  .tst-sem { margin:auto 0; padding:6px 0; font-size:14px; line-height:1.4; font-weight:500; color:#7a4708; }
  .selo { display:inline-block; align-self:flex-start; padding:3px 9px; border-radius:7px; font-size:12.5px; font-weight:700; line-height:1.35; }
  .gr-colunas { display:flex; align-items:flex-end; justify-content:space-around; gap:10px; height:124px; border-bottom:1px solid #c3cad8; }
  .gr-grupo { display:flex; flex:1; align-items:flex-end; justify-content:center; gap:4px; min-width:0; height:100%; }
  .gr-col { display:flex; flex:1; flex-direction:column; align-items:center; justify-content:flex-end; min-width:0; max-width:64px; height:100%; }
  .gr-col > b { margin-bottom:3px; font-size:12.5px; font-weight:700; line-height:1; white-space:nowrap; color:#0f172a; }
  .gr-col > i { display:block; width:100%; min-height:2px; border-radius:4px 4px 0 0; }
  .gr-eixo { display:flex; justify-content:space-around; gap:10px; padding-top:5px; font-size:12px; line-height:1.2; color:#475569; }
  .gr-eixo > span { flex:1; min-width:0; text-align:center; }
  .gr-legenda { display:flex; flex-wrap:wrap; gap:3px 12px; margin-bottom:6px; font-size:12px; color:#0f172a; }
  .gr-legenda > span { display:inline-flex; align-items:center; gap:5px; }
  .gr-legenda i { display:block; width:10px; height:10px; border-radius:3px; }
  .gr-linha { position:relative; height:112px; border-bottom:1px solid #c3cad8; }
  .gr-linha > img { position:absolute; inset:0; display:block; width:100%; height:100%; }
  .gr-ponto { position:absolute; width:9px; height:9px; border-radius:50%; background:#2343c8; transform:translate(-50%,-50%); }
  .gr-ponto.ultimo { width:13px; height:13px; border:2px solid #fff; box-shadow:0 0 0 1px #2343c8; }
  .gr-rotulo { position:absolute; font-size:12.5px; font-weight:700; line-height:1; white-space:nowrap; color:#0f172a; transform:translate(-50%,-160%); }
  .gr-datas { position:relative; height:21px; }
  .gr-datas > span { position:absolute; top:5px; font-size:12px; line-height:1.2; white-space:nowrap; color:#475569; transform:translateX(-50%); }
  .gr-h { display:grid; grid-template-columns:auto minmax(0,1fr); gap:7px 9px; align-items:center; font-size:12.5px; color:#475569; }
  .gr-trilho { display:flex; align-items:center; gap:7px; min-width:0; }
  .gr-trilho > i { display:block; flex-shrink:0; min-width:3px; height:20px; border-radius:0 5px 5px 0; }
  .gr-trilho > b { font-weight:700; white-space:nowrap; color:#0f172a; }
  .radar { position:relative; width:100%; max-width:620px; margin:auto; aspect-ratio:100 / 80; container-type:inline-size; }
  .radar > img { position:absolute; inset:0; display:block; width:100%; height:100%; }
  .radar-rotulo { position:absolute; width:max-content; max-width:25cqi; font-size:clamp(12px,3.2cqi,16px); font-weight:600; line-height:1.15; color:#0f172a; }
  .radar-rotulo > b { display:block; font-size:clamp(16px,4.6cqi,23px); font-weight:800; line-height:1.1; color:#12228e; }
  .radar-rotulo.sem { color:#7a4708; }
  .radar-rotulo.sem > b { font-size:clamp(12px,3cqi,14px); font-weight:600; color:#7a4708; }
  .radar-legenda { display:flex; flex-wrap:wrap; justify-content:center; gap:5px 18px; font-size:13.5px; color:#0f172a; }
  .radar-legenda > span { display:inline-flex; align-items:center; gap:7px; }
  .dupla { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
  .tabelas { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
  .tabela-rolagem { overflow-x:auto; border:1px solid #dbe0f0; border-radius:10px; background:#fff; }
  .tab { width:100%; border-collapse:collapse; font-size:13px; line-height:1.25; color:#0f172a; }
  .tab th { padding:7px 10px; background:#f3f5fd; font-weight:600; text-align:left; white-space:nowrap; color:#475569; }
  .tab td { padding:5px 10px; border-top:1px solid #eef1f6; white-space:nowrap; }
  .tab td:first-child { font-weight:600; white-space:normal; }
  .tab .melhorou { font-weight:700; color:#0d5132; }
  .tab .piorou { font-weight:700; color:#a8421a; }
  .tab .neutro { color:#64748b; }
  @media (max-width:1250px) {
    .cartoes.c4, .cartoes.c3 { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .tabelas { grid-template-columns:minmax(0,1fr); }
  }
  @media (max-width:900px) {
    .grupo { grid-column:1 / -1; }
    .dupla { grid-template-columns:minmax(0,1fr); }
  }
  @media (max-width:620px) {
    .cartoes.c4, .cartoes.c3, .cartoes.c2 { grid-template-columns:minmax(0,1fr); }
    .largo { grid-column:auto; }
  }
"""


# ---------------------------------------------------------------- formatação
def num(valor) -> str:
    return f"{float(valor):.2f}".rstrip("0").rstrip(".").replace(".", ",")


def unidade(texto: str | None, valor=None) -> str:
    """A API traz esta unidade sem acento e sempre no plural."""
    if texto == "desequilibrios":
        return "desequilíbrio" if valor is not None and float(valor) == 1 else "desequilíbrios"
    return texto or ""


def com_unidade(valor, texto: str | None) -> str:
    return f"{num(valor)} {unidade(texto, valor)}".strip()


def data_curta(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%y")


def data_longa(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _imagem_svg(svg: str, descricao: str = "") -> str:
    """O st.html remove SVG direto na página; como imagem, ele passa e continua nítido."""
    dados = base64.b64encode(svg.encode("utf-8")).decode()
    return f'<img alt="{escape(descricao)}" src="data:image/svg+xml;base64,{dados}">'


def _direcao(maior_melhor) -> str:
    return {True: "Quanto maior, melhor", False: "Quanto menor, melhor"}.get(maior_melhor, "Acompanhamento")


# ---------------------------------------------------------------- blocos pequenos
ESTILO_SELO = {"melhora": ("#dcf3e2", "#0d5132"), "queda": ("#fdeadf", "#a8421a"), "neutro": ("#f1f4f9", "#475569")}


def selo(etiqueta: tuple[str, str] | None) -> str:
    if not etiqueta:
        return ""
    fundo, tinta = ESTILO_SELO[etiqueta[1]]
    return f'<span class="selo" style="background:{fundo};color:{tinta}">{escape(etiqueta[0])}</span>'


def aviso(titulo: str, texto: str = "") -> str:
    corpo = f"<strong>{escape(titulo)}</strong>" + (f" {escape(texto)}" if texto else "")
    return f'<div class="aviso" role="status"><span class="aviso-marca" aria-hidden="true">!</span><div>{corpo}</div></div>'


def tile(valor, rotulo, detalhe, cor="#fff", em_texto=False) -> str:
    return (f'<div class="heroi-tile"><b class="{"texto" if em_texto else ""}" style="color:{cor}">{valor}</b>'
            f"<span>{rotulo}</span><small>{detalhe}</small></div>")


def heroi(rotulo, frase, tiles) -> str:
    return (f'<section class="heroi"><div><div class="heroi-rotulo">{rotulo}</div><p class="heroi-frase">{frase}</p></div>'
            f'<div class="heroi-tiles">{"".join(tiles)}</div></section>')


def titulo_de_painel(titulo: str, explicacao: str = "") -> str:
    return (f'<div><div class="painel-titulo">{escape(titulo)}</div>'
            + (f'<div class="painel-sub">{escape(explicacao)}</div>' if explicacao else "") + "</div>")


def diferenca_entre_lados(linhas: list[dict]) -> tuple[str, str] | None:
    ultima = max(l["data_avaliacao"] for l in linhas)
    valores = {l["lado"]: float(l["valor"]) for l in linhas if l["data_avaliacao"] == ultima and l["lado"]}
    if len(valores) < 2:
        return ("Falta uma das pernas: sem como comparar", "neutro")
    if not max(valores.values()):
        return None
    diferenca = (1 - min(valores.values()) / max(valores.values())) * 100
    texto = f"Diferença entre as pernas: {diferenca:.0f}%"
    return (f"{texto}, acima do limite de {ASSIMETRIA_LIMITE}%", "queda") if diferenca > ASSIMETRIA_LIMITE else (texto, "melhora")


# ---------------------------------------------------------------- gráficos
def _coluna(valor: float, maior: float, texto: str, cor: str, dica: str = "") -> str:
    altura = 78 * valor / maior if maior else 0
    return (f'<div class="gr-col" title="{escape(dica or texto)}"><b>{escape(texto)}</b>'
            f'<i style="height:{altura:.1f}%;background:{cor}"></i></div>')


def _eixo(rotulos: list[str]) -> str:
    return '<div class="gr-eixo">' + "".join(f"<span>{escape(r)}</span>" for r in rotulos) + "</div>"


def _legenda(itens: list[tuple[str, str]]) -> str:
    return ('<div class="gr-legenda">' + "".join(f'<span><i style="background:{cor}"></i>{escape(nome)}</span>' for nome, cor in itens) + "</div>")


def _colunas(ordenadas: list[dict]) -> str:
    """Duas avaliações: antes e agora. A última fica mais forte."""
    maior = max(float(l["valor"]) for l in ordenadas)
    colunas = "".join(
        _coluna(float(l["valor"]), maior, num(l["valor"]), AZUL if i == len(ordenadas) - 1 else AZUL_CLARO, f"{data_longa(l['data_avaliacao'])}: {com_unidade(l['valor'], l['unidade_medida'])}")
        for i, l in enumerate(ordenadas))
    return f'<div class="gr-colunas">{colunas}</div>' + _eixo([data_curta(l["data_avaliacao"]) for l in ordenadas])


def _linha(ordenadas: list[dict]) -> str:
    """3 avaliações ou mais: linha com o valor escrito em cada ponto. Dispensa o eixo vertical."""
    valores = [float(l["valor"]) for l in ordenadas]
    menor, maior = min(valores), max(valores)
    amplitude = (maior - menor) or 1
    n = len(valores)
    xs = [8 + 84 * i / (n - 1) for i in range(n)]
    ys = [50.0 if maior == menor else 84 - 56 * (v - menor) / amplitude for v in valores]
    caminho = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(xs, ys))
    linha = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none">'
             f'<polyline points="{caminho}" fill="none" stroke="{AZUL}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')
    pontos = "".join(
        f'<span class="gr-ponto{" ultimo" if i == n - 1 else ""}" style="left:{xs[i]:.2f}%;top:{ys[i]:.2f}%" title="{escape(data_longa(l["data_avaliacao"]))}: {escape(com_unidade(l["valor"], l["unidade_medida"]))}"></span>'
        f'<span class="gr-rotulo" style="left:{xs[i]:.2f}%;top:{ys[i]:.2f}%">{escape(num(l["valor"]))}</span>'
        for i, l in enumerate(ordenadas))
    # Com muitas avaliações, as datas do meio não cabem: ficam a primeira, a última e a dica no ponto.
    datas = "".join(f'<span style="left:{xs[i]:.2f}%">{escape(data_curta(l["data_avaliacao"]))}</span>'
                    for i, l in enumerate(ordenadas) if n <= 5 or i in (0, n - 1))
    return f'<div class="gr-linha">{_imagem_svg(linha)}{pontos}</div><div class="gr-datas">{datas}</div>'


def _barras(itens: list[tuple[str, float, str, str]]) -> str:
    """Barras deitadas, cada uma com o nome e o valor: (nome, valor, texto, cor)."""
    maior = max(v for _, v, _, _ in itens) or 1
    return '<div class="gr-h">' + "".join(
        f'<span>{escape(nome)}</span><span class="gr-trilho"><i style="width:{68 * valor / maior:.1f}%;background:{cor}"></i><b>{escape(texto)}</b></span>'
        for nome, valor, texto, cor in itens) + "</div>"


def _contra_a_media(linha: dict, media: float | None) -> str:
    """Uma avaliação só: não há evolução, mas dá para comparar com os colegas."""
    if media is None:
        return '<div class="tst-rodape">Poucos colegas com este teste para comparar.</div>'
    def texto(valor):
        return num(valor) if len(linha["unidade_medida"] or "") > 6 else com_unidade(valor, linha["unidade_medida"])
    return _barras([("Este atleta", float(linha["valor"]), texto(linha["valor"]), AZUL),
                    ("Média do grupo", media, texto(round(media, 1)), CINZA_GRUPO)])


def _colunas_agrupadas(grupos: list[tuple[str, list[tuple[float, str, str, str]]]]) -> str:
    """Cada grupo com as suas colunas: (valor, texto, cor, dica)."""
    maior = max((v for _, colunas in grupos for v, _, _, _ in colunas), default=1) or 1
    corpo = "".join(
        '<div class="gr-grupo">' + "".join(_coluna(v, maior, texto, cor, dica) for v, texto, cor, dica in colunas) + "</div>"
        for _, colunas in grupos)
    return f'<div class="gr-colunas">{corpo}</div>' + _eixo([nome for nome, _ in grupos])


def _tons_de_azul(n: int) -> list[str]:
    return ["#d5dcf5", AZUL_CLARO, "#6f84dc", AZUL][-n:]


# ---------------------------------------------------------------- cartões de teste
def _cartao_vazio(nome: str, classe: str = "") -> str:
    return (f'<div class="tst vazio {classe}"><div class="tst-nome">{escape(nome)}</div>'
            '<div class="tst-sem">Sem dados: o atleta ainda não fez este teste.</div></div>')


def _cartao_de_teste(teste: str, por_teste: dict, ids: list[str], ultimos: dict, uma_so_no_atleta: bool) -> str:
    linhas = por_teste.get(teste)
    if not linhas:
        return _cartao_vazio(NOMES_DE_TESTE.get(teste, teste))
    ordenadas = sorted(linhas, key=lambda l: l["data_avaliacao"])
    atual = ordenadas[-1]
    n = len(ordenadas)
    if n == 1:
        desenho = _contra_a_media(atual, leitura.media_no_grupo(linhas, ids, ultimos))
        etiqueta = None if uma_so_no_atleta else ("Só 1 avaliação neste teste: sem evolução", "neutro")
    else:
        desenho = _colunas(ordenadas) if n == 2 else _linha(ordenadas)
        etiqueta = leitura.tendencia(linhas)
    posicao = leitura.posicao_no_teste(linhas, ids, ultimos)
    rodape = f"Última: {data_longa(atual['data_avaliacao'])}" + (f" · {posicao[0]}º de {posicao[1]} colegas" if posicao else "")
    return (f'<div class="tst"><div><div class="tst-nome">{escape(atual["teste_nome"])}</div><div class="tst-dica">{_direcao(atual["maior_melhor"])}</div></div>'
            f'<div class="tst-valor">{escape(num(atual["valor"]))} <small>{escape(unidade(atual["unidade_medida"], atual["valor"]))}</small></div>'
            f'{selo(etiqueta)}<div class="tst-grafico">{desenho}</div><div class="tst-rodape">{escape(rodape)}</div></div>')


def _cartao_de_lados(teste: str, por_teste: dict) -> str:
    linhas = por_teste.get(teste)
    if not linhas:
        return _cartao_vazio(NOMES_DE_TESTE[teste])
    datas = sorted({l["data_avaliacao"] for l in linhas})
    if len(datas) == 1:
        desenho = _barras([(LADOS[l["lado"]], float(l["valor"]), com_unidade(l["valor"], l["unidade_medida"]), AZUL if l["lado"] == "dir" else VERDE)
                           for l in sorted(linhas, key=lambda l: l["lado"] or "")])
    else:
        grupos = []
        for data in datas[-MAXIMO_DE_DATAS:]:
            do_dia = {l["lado"]: l for l in linhas if l["data_avaliacao"] == data}
            grupos.append((data_curta(data), [
                (float(do_dia[lado]["valor"]), num(do_dia[lado]["valor"]), AZUL if lado == "dir" else VERDE,
                 f"{LADOS[lado]}, {data_longa(data)}: {com_unidade(do_dia[lado]['valor'], do_dia[lado]['unidade_medida'])}")
                for lado in ("dir", "esq") if lado in do_dia]))
        desenho = _legenda([("Direita", AZUL), ("Esquerda", VERDE)]) + _colunas_agrupadas(grupos)
    return (f'<div class="tst"><div><div class="tst-nome">{escape(linhas[0]["teste_nome"])}</div><div class="tst-dica">Quanto maior, melhor. Em centímetros</div></div>'
            f'{selo(diferenca_entre_lados(linhas))}<div class="tst-grafico">{desenho}</div><div class="tst-rodape">Última: {data_longa(datas[-1])}</div></div>')


def _cartao_de_saltos(por_teste: dict, ids: list[str], ultimos: dict) -> str:
    """Os três saltos têm a mesma unidade: num gráfico só, comparam entre si."""
    presentes = [t for t in TESTES_DE_SALTO if por_teste.get(t)]
    if not presentes:
        return _cartao_vazio("Saltos verticais", "largo")
    datas = sorted({l["data_avaliacao"] for t in presentes for l in por_teste[t]})
    grupos = []
    if len(datas) == 1:
        for teste in presentes:
            linha = por_teste[teste][0]
            valor = float(linha["valor"])
            colunas = [(valor, num(valor), AZUL, f"Este atleta: {num(valor)} cm")]
            media = leitura.media_no_grupo(por_teste[teste], ids, ultimos)
            if media is not None:
                colunas.append((media, num(round(media, 1)), CINZA_GRUPO, f"Média do grupo: {num(round(media, 1))} cm"))
            grupos.append((NOMES_DE_SALTO[teste], colunas))
        legenda = _legenda([("Este atleta", AZUL), ("Média do grupo", CINZA_GRUPO)])
    else:
        usadas = datas[-MAXIMO_DE_DATAS:]
        tons = _tons_de_azul(len(usadas))
        for teste in presentes:
            por_data = {l["data_avaliacao"]: l for l in por_teste[teste]}
            grupos.append((NOMES_DE_SALTO[teste], [
                (float(por_data[d]["valor"]), num(por_data[d]["valor"]), tons[i], f"{data_longa(d)}: {num(por_data[d]['valor'])} cm")
                for i, d in enumerate(usadas) if d in por_data]))
        legenda = _legenda([(data_curta(d), tons[i]) for i, d in enumerate(usadas)])
    return ('<div class="tst largo"><div><div class="tst-nome">Saltos verticais</div><div class="tst-dica">Quanto maior, melhor. Em centímetros</div></div>'
            f'<div class="tst-grafico">{legenda}{_colunas_agrupadas(grupos)}</div></div>')


def painel_de_evolucao(linhas: list[dict], ids: list[str], ultimos: dict, one_to_one: bool = False) -> str:
    """Todos os testes, sempre no mesmo lugar: o professor acha cada um em qualquer atleta."""
    por_teste: dict[str, list[dict]] = {}
    for linha in linhas:
        por_teste.setdefault(linha["teste"], []).append(linha)
    uma_so = len({l["data_avaliacao"] for l in linhas}) == 1

    def cartao(chave):
        if chave == "saltos":
            return _cartao_de_saltos(por_teste, ids, ultimos)
        if chave in TESTES_DE_LADO:
            return _cartao_de_lados(chave, por_teste)
        return _cartao_de_teste(chave, por_teste, ids, ultimos, uma_so)

    return '<div class="grupos">' + "".join(
        f'<section class="grupo {largura}"><div class="grupo-nome">{escape(nome)}</div>'
        f'<div class="cartoes c{colunas}">{"".join(cartao(c) for c in chaves)}</div></section>'
        for nome, largura, colunas, chaves in (GRUPOS_ONE_TO_ONE if one_to_one else GRUPOS)) + "</div>"


# ---------------------------------------------------------------- tabela compacta
def tabela_de_valores(linhas: list[dict], comparacao: list[dict]) -> str:
    """Todos os valores em duas colunas de linhas curtas, para ocupar pouco espaço."""
    datas = sorted({l["data_avaliacao"] for l in linhas})[-MAXIMO_DE_DATAS:]
    valores: dict[tuple, dict] = {}
    for l in linhas:
        valores.setdefault((l["teste"], l["lado"]), {})[l["data_avaliacao"]] = l
    variacoes = {(l["teste"], l["lado"]): l for l in comparacao}
    ordem = {t: i for i, t in enumerate(ORDEM_DOS_TESTES)}
    chaves = sorted(valores, key=lambda c: (ordem.get(c[0], 99), c[1] or ""))
    tem_comparacao = len(datas) >= 2

    def linha_da_tabela(chave):
        por_data = valores[chave]
        qualquer = next(iter(por_data.values()))
        lado = LADOS.get(chave[1])
        nome = escape(qualquer["teste_nome"] + (f" · {lado.lower()}" if lado else ""))
        celulas = "".join(f"<td>{escape(com_unidade(por_data[d]['valor'], por_data[d]['unidade_medida'])) if d in por_data else '—'}</td>" for d in datas)
        fim = ""
        if tem_comparacao:
            c = variacoes.get(chave)
            situacao = c["situacao"] if c else None
            rotulo = {"melhorou": "Melhorou", "piorou": "Piorou", "estavel": "Estável",
                      "sem_classificacao": "Sentido a definir"}.get(situacao, "Sem comparação")
            if c and c["variacao_pct"] is not None and situacao in ("melhorou", "piorou"):
                rotulo += f" {abs(float(c['variacao_pct'])):.1f}%".replace(".", ",")
            if c and not c["confirmado"] and situacao in ("melhorou", "piorou", "estavel"):
                rotulo += " *"
            fim = f'<td class="{situacao if situacao in ("melhorou", "piorou") else "neutro"}">{escape(rotulo)}</td>'
        return f"<tr><td>{nome}</td>{celulas}{fim}</tr>"

    cabecalho = ("<tr><th>Teste</th>" + "".join(f"<th>{data_curta(d)}</th>" for d in datas)
                 + ("<th>Contra a anterior</th>" if tem_comparacao else "") + "</tr>")
    metade = math.ceil(len(chaves) / 2)
    tabelas = "".join(
        f'<div class="tabela-rolagem"><table class="tab"><thead>{cabecalho}</thead><tbody>{"".join(linha_da_tabela(c) for c in parte)}</tbody></table></div>'
        for parte in (chaves[:metade], chaves[metade:]) if parte)
    notas = []
    if not tem_comparacao:
        notas.append("Só há uma avaliação: ainda não há mudança para mostrar.")
    if len({l["data_avaliacao"] for l in linhas}) > MAXIMO_DE_DATAS:
        notas.append(f"A tabela mostra as {MAXIMO_DE_DATAS} últimas avaliações.")
    if any(not c["confirmado"] and c["situacao"] in ("melhorou", "piorou", "estavel") for c in comparacao):
        notas.append("* A PKZ ainda não confirmou a regra deste teste. Não use essa classificação no relatório dos pais.")
    return (f'<div class="tabelas">{tabelas}</div>'
            + (f'<div class="tst-rodape" style="margin-top:8px">{escape(" ".join(notas))}</div>' if notas else ""))


# ---------------------------------------------------------------- listas
def destaques(perfil: list[dict], maximo: int = 3) -> str:
    """Melhores e piores resultados como posição entre os colegas: "2º de 11" dispensa explicação."""
    if len(perfil) < 2:
        return aviso("Sem dados suficientes para comparar.", "Ainda não há colegas suficientes nos mesmos testes.")

    def lista(itens, titulo, tinta, fundo):
        linhas = "".join(
            f'<div style="display:flex;align-items:center;gap:11px;padding:9px 0;border-top:1px solid #eef1f6">'
            f'<span style="flex-shrink:0;min-width:84px;padding:4px 8px;border-radius:8px;background:{fundo};color:{tinta};text-align:center;font-size:clamp(12.5px,.92vw,15px);font-weight:800">{p["posicao"]}º de {p["total"]}</span>'
            f'<span style="min-width:0"><span style="display:block;font-size:clamp(13.5px,1vw,16px);font-weight:600;color:{TINTA}">{escape(p["teste"])}</span>'
            f'<span style="font-size:clamp(12px,.85vw,13.5px);color:{TINTA_FRACA}">{escape(com_unidade(p["valor"], p["unidade"]))}</span></span></div>'
            for p in itens)
        return (f'<div style="flex:1;min-width:250px"><div style="margin-bottom:6px;font-size:clamp(14px,1.05vw,17px);font-weight:700;color:{tinta}">{titulo}</div>{linhas}</div>')
    tamanho = min(maximo, len(perfil) // 2)
    return ('<div style="display:flex;flex-wrap:wrap;gap:14px 26px">'
            + lista(perfil[:tamanho], "Melhores resultados", "#0d5132", "#dcf3e2")
            + lista(list(reversed(perfil[-tamanho:])), "Precisa de atenção", "#a8421a", "#fdeadf") + "</div>")


def mudancas_em_lista(itens: list[dict], maximo: int = 6) -> str:
    """Antes e agora, em duas listas: o valor real é o que o professor compara na cabeça."""
    def lista(grupo, titulo, tinta, fundo, marca):
        if not grupo:
            return ""
        linhas = "".join(
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid #eef1f6">'
            f'<span style="min-width:0;font-size:clamp(13.5px,1vw,16px);font-weight:600;color:{TINTA}">{escape(i["teste"])}</span>'
            f'<span style="flex-shrink:0;font-size:clamp(13px,.95vw,15.5px);color:{TINTA_FRACA}">{escape(num(i["anterior"]))} → '
            f'<strong style="font-weight:800;color:{TINTA}">{escape(num(i["atual"]))}</strong> {escape(unidade(i["unidade"], i["atual"]))}</span></div>'
            for i in grupo[:maximo])
        resto = (f'<div style="padding-top:7px;font-size:12.5px;color:{TINTA_FRACA}">e mais {len(grupo) - maximo}, na tabela abaixo</div>'
                 if len(grupo) > maximo else "")
        return (f'<div style="flex:1;min-width:270px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:clamp(14px,1.05vw,17px);font-weight:700;color:{tinta}">'
                f'<span aria-hidden="true" style="display:grid;place-items:center;width:24px;height:24px;border-radius:7px;background:{fundo}">{marca}</span>{titulo} ({len(grupo)})</div>{linhas}{resto}</div>')
    melhorou = [i for i in itens if i["situacao"] == "Melhorou"]
    piorou = sorted((i for i in itens if i["situacao"] == "Piorou"), key=lambda i: i["ganho"])
    estaveis = sum(i["situacao"] == "Estável" for i in itens)
    nota = (f'<div style="margin-top:9px;font-size:clamp(12.5px,.9vw,14px);color:{TINTA_FRACA}">{estaveis} '
            f'{"teste ficou estável" if estaveis == 1 else "testes ficaram estáveis"}.</div>') if estaveis else ""
    return ('<div style="display:flex;flex-wrap:wrap;gap:14px 26px">'
            + lista(melhorou, "Melhorou", "#0d5132", "#dcf3e2", "▲") + lista(piorou, "Piorou", "#a8421a", "#fdeadf", "▼") + f"</div>{nota}")


# ---------------------------------------------------------------- radar
def radar(cartao: dict) -> str:
    """Radar dos atributos, leitura comum no esporte. Todo atleta da modalidade tem os mesmos eixos.

    A simetria não entra: ela usa outra escala, quase sempre perto de 100, e criaria um pico falso.
    Os nomes ficam em HTML por cima do desenho, para não encolher junto com a imagem.
    """
    eixos = [(d["nome"], cartao["atributos"][d["sigla"]], cartao["medias"][d["sigla"]])
             for d in cartao["definicoes"] if d["tipo"] != "simetria"]
    tem_desenho = sum(e[1] is not None for e in eixos) >= 3
    tem_grupo = sum(e[2] is not None for e in eixos) >= 3
    cx, cy, raio = 50, 41, 29
    n = len(eixos)

    def xy(i, valor):
        angulo = -math.pi / 2 + 2 * math.pi * i / n
        r = raio * valor / 100
        return cx + r * math.cos(angulo), cy + r * math.sin(angulo)

    def poligono(indices_valores):
        return " ".join(f"{xy(i, v)[0]:.2f},{xy(i, v)[1]:.2f}" for i, v in indices_valores)

    aneis = "".join(f'<polygon points="{poligono((i, v) for i in range(n))}" fill="none" stroke="#e1e5f0" stroke-width=".3"/>' for v in (25, 50, 75, 100))
    raios = "".join(f'<line x1="{cx}" y1="{cy}" x2="{xy(i, 100)[0]:.2f}" y2="{xy(i, 100)[1]:.2f}" stroke="#e1e5f0" stroke-width=".3"/>' for i in range(n))
    do_grupo = (f'<polygon points="{poligono((i, e[2]) for i, e in enumerate(eixos) if e[2] is not None)}" fill="none" stroke="#7c879e" stroke-width=".5" stroke-dasharray="1.3 1"/>'
                if tem_grupo else "")
    do_atleta = ""
    if tem_desenho:
        vertices = "".join(f'<circle cx="{xy(i, e[1])[0]:.2f}" cy="{xy(i, e[1])[1]:.2f}" r="1.05" fill="{AZUL}" stroke="#fff" stroke-width=".35"/>'
                           for i, e in enumerate(eixos) if e[1] is not None)
        do_atleta = (f'<polygon points="{poligono((i, e[1]) for i, e in enumerate(eixos) if e[1] is not None)}" fill="{AZUL}" fill-opacity=".22" stroke="{AZUL}" stroke-width=".65" stroke-linejoin="round"/>{vertices}')
    desenho = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80">{aneis}{raios}{do_grupo}{do_atleta}</svg>'

    rotulos = []
    for i, (nome, valor, _) in enumerate(eixos):
        x, y = xy(i, 112)
        if abs(x - cx) < 4:
            posicao, alinhamento = ("translate(-50%,-100%)" if y < cy else "translate(-50%,0)"), "center"
        elif x > cx:
            posicao, alinhamento = "translate(0,-50%)", "left"
        else:
            posicao, alinhamento = "translate(-100%,-50%)", "right"
        texto = "sem dado" if valor is None else valor
        rotulos.append(f'<div class="radar-rotulo{" sem" if valor is None else ""}" style="left:{x:.2f}%;top:{y / 80 * 100:.2f}%;transform:{posicao};text-align:{alinhamento}">'
                       f"{escape(nome)}<b>{texto}</b></div>")
    descricao = "Radar dos atributos: " + ", ".join(f"{e[0]} {'sem dado' if e[1] is None else e[1]}" for e in eixos)
    alerta = "" if tem_desenho else aviso("Sem dados suficientes para o perfil.", "O desenho do atleta aparece com pelo menos 3 atributos preenchidos.")
    return (f'{alerta}<div class="radar">{_imagem_svg(desenho, descricao)}{"".join(rotulos)}</div>'
            f'<div class="radar-legenda"><span><span aria-hidden="true" style="width:20px;height:4px;border-radius:2px;background:{AZUL}"></span>Este atleta</span>'
            '<span><span aria-hidden="true" style="width:20px;border-top:2px dashed #7c879e"></span>Média do grupo</span></div>')
