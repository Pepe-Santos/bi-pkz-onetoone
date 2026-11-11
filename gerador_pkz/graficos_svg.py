"""Gráficos SVG dos relatórios HTML.

Usam a paleta e a tipografia dos SVGs dos modelos oficiais (templates/referencia).
Todo texto vindo dos dados passa por escape.
"""
import math

from markupsafe import Markup, escape

COR_VERDE = "#157a4b"
COR_VERMELHO = "#be123c"
COR_AZUL = "#0e1a6b"
COR_BARRA = "#c9d3e8"
COR_GRADE = "#eef1f6"
COR_EIXO = "#94a3b8"
COR_TEXTO = "#0f172a"
COR_TEXTO_SUAVE = "#475569"


def _t(valor):
    return str(escape(valor))


def _num(valor):
    texto = f"{valor:.1f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _teto(maximo):
    """Teto do eixo: inteiro par até 100 (meios-passos inteiros); acima, valor 'redondo'."""
    if maximo <= 2:
        return 2
    if maximo <= 100:
        inteiro = math.ceil(maximo)
        return inteiro + inteiro % 2
    expoente = 10 ** math.floor(math.log10(maximo))
    for fator in (1, 1.2, 1.5, 2, 3, 4, 5, 6, 8, 10):
        if fator * expoente >= maximo:
            return fator * expoente
    return maximo


def barras_empilhadas(baldes, largura=740, altura=200):
    """Barras empilhadas (ex.: presenças e faltas por semana ou mês).

    baldes: lista de dicts {rotulo, sub (opcional), partes: [(valor, cor), ...]}.
    """
    if not baldes:
        return None
    topo, base = 22, altura - 48
    area = base - topo
    esquerda, direita = 40, largura - 10
    totais = [sum(v for v, _ in b["partes"]) for b in baldes]
    maximo = _teto(max(totais) if totais else 1)
    passo = (direita - esquerda) / len(baldes)
    larg_barra = min(78, passo * 0.62)

    svg = [
        f'<svg viewBox="0 0 {largura} {altura}" style="display:block; width:100%; height:auto" '
        f'font-family="Inter, sans-serif">'
    ]
    for fracao in (0, 0.5, 1):
        y = base - area * fracao
        svg.append(f'<line x1="{esquerda}" y1="{y:.1f}" x2="{direita}" y2="{y:.1f}" stroke="{COR_GRADE}" stroke-width="1"/>')
        svg.append(
            f'<text x="{esquerda - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COR_EIXO}">'
            f'{_num(maximo * fracao)}</text>'
        )
    for i, balde in enumerate(baldes):
        cx = esquerda + passo * (i + 0.5)
        x = cx - larg_barra / 2
        y_atual = base
        for valor, cor in balde["partes"]:
            if valor <= 0:
                continue
            h = area * valor / maximo
            y_atual -= h
            svg.append(
                f'<rect x="{x:.1f}" y="{y_atual:.1f}" width="{larg_barra:.1f}" height="{h:.1f}" fill="{cor}"/>'
            )
            if h >= 16:
                svg.append(
                    f'<text x="{cx:.1f}" y="{y_atual + h / 2 + 4:.1f}" text-anchor="middle" font-size="12" '
                    f'font-weight="700" fill="#fff">{_num(valor)}</text>'
                )
        svg.append(
            f'<text x="{cx:.1f}" y="{base + 17}" text-anchor="middle" font-size="12.5" font-weight="600" '
            f'fill="{COR_TEXTO}">{_t(balde["rotulo"])}</text>'
        )
        if balde.get("sub"):
            svg.append(
                f'<text x="{cx:.1f}" y="{base + 32}" text-anchor="middle" font-size="11" '
                f'fill="{COR_TEXTO_SUAVE}">{_t(balde["sub"])}</text>'
            )
    svg.append("</svg>")
    return Markup("".join(svg))


def linha_evolucao(pontos, unidade="", largura=360, altura=140):
    """Linha com os valores confirmados de um teste.

    pontos: lista de (rotulo_data, valor) em ordem cronológica (>= 2 pontos).
    """
    if len(pontos) < 2:
        return None
    esquerda, direita, topo, base = 14, largura - 14, 26, altura - 28
    valores = [v for _, v in pontos]
    menor, maior = min(valores), max(valores)
    faixa = (maior - menor) or 1.0
    # folga vertical para os rótulos não encostarem nas bordas
    def y_de(v):
        return base - (base - topo) * ((v - menor) / faixa) * 0.82 - 6

    passo = (direita - esquerda) / (len(pontos) - 1)
    coords = [(esquerda + passo * i, y_de(v)) for i, (_, v) in enumerate(pontos)]
    svg = [
        f'<svg viewBox="0 0 {largura} {altura}" style="display:block; width:100%; height:auto" '
        f'font-family="Inter, sans-serif">',
        f'<line x1="{esquerda}" y1="{base}" x2="{direita}" y2="{base}" stroke="{COR_GRADE}" stroke-width="1"/>',
        f'<polyline fill="none" stroke="{COR_AZUL}" stroke-width="2.5" points="'
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        + '"/>',
    ]
    for i, ((x, y), (rotulo, valor)) in enumerate(zip(coords, pontos)):
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#fff" stroke="{COR_AZUL}" stroke-width="2.5"/>')
        ancora = "start" if i == 0 else "end" if i == len(pontos) - 1 else "middle"
        x_txt = x - 4 if i == 0 else x + 4 if i == len(pontos) - 1 else x
        # rótulo de valor só nas pontas e, se poucos pontos, em todos
        if i in (0, len(pontos) - 1) or len(pontos) <= 4:
            svg.append(
                f'<text x="{x_txt:.1f}" y="{y - 9:.1f}" text-anchor="{ancora}" font-size="11.5" font-weight="700" '
                f'fill="{COR_AZUL}" paint-order="stroke" stroke="#fff" stroke-width="3" stroke-linejoin="round">'
                f'{_num(valor)}</text>'
            )
        if i in (0, len(pontos) - 1) or len(pontos) <= 4:
            svg.append(
                f'<text x="{x_txt:.1f}" y="{base + 15}" text-anchor="{ancora}" font-size="10.5" '
                f'fill="{COR_TEXTO_SUAVE}">{_t(rotulo)}</text>'
            )
    svg.append("</svg>")
    return Markup("".join(svg))


def barra_antes_agora(anterior, atual, cor=COR_AZUL, largura=220):
    """Barra do valor atual com um risco no valor anterior (como nos modelos)."""
    if anterior is None or atual is None:
        return None
    maximo = max(abs(anterior), abs(atual)) or 1
    xa = largura * abs(atual) / maximo
    xp = largura * abs(anterior) / maximo
    return Markup(
        f'<svg viewBox="0 0 {largura} 14" style="display:block; width:100%; height:14px" preserveAspectRatio="none">'
        f'<rect x="0" y="3" width="{largura}" height="8" rx="4" fill="{COR_GRADE}"/>'
        f'<rect x="0" y="3" width="{xa:.1f}" height="8" rx="4" fill="{cor}"/>'
        f'<rect x="{max(xp - 1.5, 0):.1f}" y="0" width="3" height="14" rx="1" fill="{COR_AZUL}"/>'
        f"</svg>"
    )


def rosca(partes, largura=740, altura=210):
    """Rosca de proporções com legenda. partes: [(rotulo, valor, cor)]; valores zero são omitidos."""
    partes = [(r, v, c) for r, v, c in partes if v > 0]
    total = sum(v for _, v, _ in partes)
    if not total:
        return None
    raio, cx, cy, esp = 70, 120, altura / 2, 30
    circ = 2 * math.pi * raio
    svg = [f'<svg viewBox="0 0 {largura} {altura}" style="display:block; width:100%; height:auto" font-family="Inter, sans-serif">',
           f'<circle cx="{cx}" cy="{cy}" r="{raio}" fill="none" stroke="{COR_GRADE}" stroke-width="{esp}"/>']
    acumulado = 0
    for _rotulo, valor, cor in partes:
        tamanho = circ * valor / total
        svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{raio}" fill="none" stroke="{cor}" stroke-width="{esp}" '
            f'stroke-dasharray="{tamanho:.2f} {circ - tamanho:.2f}" stroke-dashoffset="{-acumulado:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        acumulado += tamanho
    svg.append(f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="30" font-weight="700" fill="{COR_TEXTO}">{total}</text>')
    svg.append(f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" font-size="11" fill="{COR_TEXTO_SUAVE}">sessões</text>')
    topo = cy - (len(partes) * 34) / 2 + 12
    for i, (rotulo, valor, cor) in enumerate(partes):
        y = topo + i * 34
        svg.append(f'<rect x="270" y="{y - 12:.1f}" width="14" height="14" rx="3" fill="{cor}"/>')
        svg.append(f'<text x="294" y="{y:.1f}" font-size="14" font-weight="600" fill="{COR_TEXTO}">{_t(rotulo)}</text>')
        svg.append(
            f'<text x="520" y="{y:.1f}" font-size="14" font-weight="700" fill="{COR_TEXTO}" text-anchor="end">{valor}</text>'
            f'<text x="590" y="{y:.1f}" font-size="13" fill="{COR_TEXTO_SUAVE}" text-anchor="end">{round(valor / total * 100)}%</text>'
        )
    svg.append("</svg>")
    return Markup("".join(svg))


def barras_variacao(itens, largura=740):
    """Barras horizontais divergentes da variação % de cada teste.

    itens: [{nome, pct, cor}] (pct positivo à direita, negativo à esquerda).
    """
    if not itens:
        return None
    linha, topo = 34, 8
    altura = topo + linha * len(itens) + 6
    x0, x1 = 270, largura - 70
    centro = (x0 + x1) / 2
    maximo = max(abs(i["pct"]) for i in itens) or 1
    escala = (x1 - x0) / 2 / maximo
    svg = [f'<svg viewBox="0 0 {largura} {altura}" style="display:block; width:100%; height:auto" font-family="Inter, sans-serif">',
           f'<line x1="{centro}" y1="2" x2="{centro}" y2="{altura - 2}" stroke="{COR_EIXO}" stroke-width="1"/>']
    for k, item in enumerate(itens):
        y = topo + k * linha
        nome = item["nome"] if len(item["nome"]) <= 34 else item["nome"][:33] + "…"
        svg.append(f'<text x="{x0 - 14}" y="{y + 19}" text-anchor="end" font-size="12.5" font-weight="600" fill="{COR_TEXTO}">{_t(nome)}</text>')
        comp = abs(item["pct"]) * escala
        x = centro if item["pct"] >= 0 else centro - comp
        svg.append(f'<rect x="{x:.1f}" y="{y + 7}" width="{max(comp, 1.5):.1f}" height="16" rx="4" fill="{item["cor"]}"/>')
        rotulo = f'{item["pct"]:+.1f}%'.replace(".", ",")
        if item["pct"] >= 0:
            svg.append(f'<text x="{x + comp + 6:.1f}" y="{y + 19}" font-size="12" font-weight="700" fill="{item["cor"]}">{rotulo}</text>')
        else:
            svg.append(f'<text x="{x - 6:.1f}" y="{y + 19}" text-anchor="end" font-size="12" font-weight="700" fill="{item["cor"]}">{rotulo}</text>')
    svg.append("</svg>")
    return Markup("".join(svg))


def calendario_mes(ano, mes, status_por_dia, largura=740):
    """Calendário do mês (segunda a domingo) colorido pelo status do dia.

    status_por_dia: {dia(int): 'presente'|'falta'|'cancelado'|'agendado'}.
    """
    import calendar as _cal

    cores = {"presente": (COR_VERDE, "#fff"), "falta": (COR_VERMELHO, "#fff"),
             "cancelado": ("#cbd5e1", COR_TEXTO), "agendado": ("#dbe4ff", COR_AZUL)}
    semanas = _cal.Calendar(firstweekday=0).monthdayscalendar(ano, mes)
    larg_cel, alt_cel, topo = (largura - 8) / 7, 46, 24
    altura = topo + alt_cel * len(semanas) + 4
    svg = [f'<svg viewBox="0 0 {largura} {altura}" style="display:block; width:100%; height:auto" font-family="Inter, sans-serif">']
    for i, nome in enumerate(["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]):
        svg.append(f'<text x="{4 + larg_cel * (i + .5):.1f}" y="14" text-anchor="middle" font-size="11.5" font-weight="600" fill="{COR_TEXTO_SUAVE}">{nome}</text>')
    for s, semana in enumerate(semanas):
        for d, dia in enumerate(semana):
            if not dia:
                continue
            x, y = 4 + larg_cel * d + 3, topo + alt_cel * s + 3
            fundo, texto = cores.get(status_por_dia.get(dia), (COR_GRADE, COR_TEXTO_SUAVE))
            svg.append(f'<rect x="{x:.1f}" y="{y}" width="{larg_cel - 6:.1f}" height="{alt_cel - 6}" rx="8" fill="{fundo}"/>')
            svg.append(f'<text x="{x + (larg_cel - 6) / 2:.1f}" y="{y + (alt_cel - 6) / 2 + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="{texto}">{dia}</text>')
    svg.append("</svg>")
    return Markup("".join(svg))
