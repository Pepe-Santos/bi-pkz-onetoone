"""Gráficos SVG dos relatórios v2, desenhados no tamanho exato do espaço que ocupam na página.

Como cada gráfico já nasce no tamanho final, o texto dentro dele tem o tamanho de letra escrito
aqui (não encolhe com o desenho) e continua legível impresso. Todas as funções recebem só números
já calculados em indicadores.py.
"""
import calendar
import math
from html import escape

FONTE = "Inter, 'Segoe UI', sans-serif"
TEXTO, SUAVE, GRADE, EIXO = "#0f172a", "#64748b", "#e8ecf3", "#cbd5e1"


def _n(v, casas=1):
    if v is None:
        return ""
    t = f"{v:.{casas}f}".replace(".", ",")
    return t.rstrip("0").rstrip(",") if "," in t else t


def _svg(w, h, corpo, descricao=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'role="img" aria-label="{escape(descricao)}" font-family="{FONTE}" style="display:block">{corpo}</svg>')


def _txt(x, y, texto, tam=11, cor=TEXTO, peso=400, ancora="middle", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{ancora}" {extra}>{escape(str(texto))}</text>')


def teto(maximo):
    """Topo do eixo: um número redondo logo acima do maior valor."""
    if maximo <= 0:
        return 1
    if maximo <= 5:
        return math.ceil(maximo)
    passo = 10 ** math.floor(math.log10(maximo))
    for m in (1, 2, 2.5, 5, 10):
        if maximo <= m * passo:
            return m * passo
    return 10 * passo


# ---------------------------------------------------------------- barras verticais (empilhadas)
def barras(colunas, w, h, unidade="", total_no_topo=True):
    """colunas: [{"rotulo", "sub", "partes": [(valor, cor)]}]. Empilha as partes; escreve cada valor."""
    if not colunas or not any(sum(v for v, _ in c["partes"]) for c in colunas):
        return None
    h = min(h, 290)  # barras altas demais exageram a diferença; o bloco centraliza o desenho
    esq, dir_, topo, base = 30, 6, 16, h - (34 if any(c.get("sub") for c in colunas) else 22)
    maior = teto(max(sum(v for v, _ in c["partes"]) for c in colunas))
    corpo = []
    for i in range(3):
        v = maior * i / 2
        y = base - (base - topo) * i / 2
        corpo.append(f'<line x1="{esq}" y1="{y:.1f}" x2="{w - dir_}" y2="{y:.1f}" stroke="{GRADE}"/>')
        corpo.append(_txt(esq - 6, y + 3.5, _n(v, 0) + unidade, 9.5, SUAVE, ancora="end"))
    n = len(colunas)
    passo = (w - esq - dir_) / n
    larg = min(passo * 0.62, 54)
    for i, c in enumerate(colunas):
        x = esq + passo * i + (passo - larg) / 2
        y = base
        total = 0
        for valor, cor in c["partes"]:
            if valor <= 0:
                continue
            altura = (base - topo) * valor / maior
            y -= altura
            total += valor
            corpo.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{larg:.1f}" height="{altura:.1f}" fill="{cor}" rx="2"/>')
            if altura >= 15 and len(c["partes"]) > 1:
                corpo.append(_txt(x + larg / 2, y + altura / 2 + 4, _n(valor, 0), 10, "#fff", 700))
        if total_no_topo and total:
            corpo.append(_txt(x + larg / 2, y - 4, _n(total, 1) + (unidade if unidade == "%" else ""), 10.5, TEXTO, 700))
        corpo.append(_txt(x + larg / 2, base + 14, c["rotulo"], 10.5, TEXTO, 600))
        if c.get("sub"):
            corpo.append(_txt(x + larg / 2, base + 27, c["sub"], 9, SUAVE))
    return _svg(w, h, "".join(corpo), "Gráfico de barras: " + ", ".join(f"{c['rotulo']} {sum(v for v, _ in c['partes'])}" for c in colunas))


# ---------------------------------------------------------------- barras horizontais
def barras_h(itens, w, h, maximo=None, divergente=False, marca=None):
    """itens: [{"rotulo", "valor", "texto", "cor"}]. Divergente: zero no meio (variações + e −).

    marca: valor de referência desenhado como um risco (ex.: 50 no percentil = meio do grupo).
    """
    itens = [dict(i) for i in itens if i["valor"] is not None]  # cópia: o rótulo é encurtado só neste desenho
    if not itens:
        return None
    cabem = max(1, int(h // 18))
    if len(itens) > cabem:  # mostra os de maior valor absoluto, na ordem original
        maiores = sorted(range(len(itens)), key=lambda k: -abs(itens[k]["valor"]))[:cabem]
        itens = [itens[k] for k in sorted(maiores)]
    rotulo_w = min(max(len(i["rotulo"]) for i in itens) * 6.3 + 10, w * 0.4)
    caracteres = max(6, int((rotulo_w - 10) / 6.3))
    for i in itens:
        if len(i["rotulo"]) > caracteres:
            i.update(rotulo=i["rotulo"][:caracteres - 1].rstrip() + "…")
    texto_w = 64
    x0, x1 = rotulo_w + (48 if divergente else 0), w - texto_w
    linha = min((h - 4) / len(itens), 30)
    barra = max(min(linha * 0.55, 15), 6)
    maior = maximo or max(abs(i["valor"]) for i in itens) or 1
    centro = (x0 + x1) / 2 if divergente else x0
    escala = ((x1 - x0) / 2 if divergente else (x1 - x0)) / maior
    corpo = []
    if divergente:
        corpo.append(f'<line x1="{centro:.1f}" y1="0" x2="{centro:.1f}" y2="{linha * len(itens):.1f}" stroke="{EIXO}"/>')
    for k, i in enumerate(itens):
        y = k * linha + (linha - barra) / 2
        comp = abs(i["valor"]) * escala
        x = centro - comp if divergente and i["valor"] < 0 else centro
        corpo.append(_txt(rotulo_w - 8, y + barra / 2 + 4, i["rotulo"], 10.5, TEXTO, 600, "end"))
        if not divergente:
            corpo.append(f'<rect x="{x0:.1f}" y="{y:.1f}" width="{x1 - x0:.1f}" height="{barra:.1f}" rx="{barra / 2:.1f}" fill="#eef1f6"/>')
        corpo.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(comp, 2):.1f}" height="{barra:.1f}" rx="{barra / 2:.1f}" fill="{i["cor"]}"/>')
        if marca is not None:
            xm = x0 + marca * escala
            corpo.append(f'<line x1="{xm:.1f}" y1="{y - 3:.1f}" x2="{xm:.1f}" y2="{y + barra + 3:.1f}" stroke="{TEXTO}" stroke-width="1.5"/>')
        tx = (x + comp + 6) if not divergente or i["valor"] >= 0 else (x - 6)
        if divergente:
            corpo.append(_txt(tx, y + barra / 2 + 4, i["texto"], 10.5, i["cor"], 700, "start" if i["valor"] >= 0 else "end"))
        else:
            corpo.append(_txt(w - 2, y + barra / 2 + 4, i["texto"], 10.5, TEXTO, 700, "end"))
    return _svg(w, min(h, linha * len(itens) + 2), "".join(corpo),
                "Barras: " + ", ".join(f"{i['rotulo']} {i['texto']}" for i in itens))


# ---------------------------------------------------------------- rosca
def rosca(partes, w, h, centro=None, centro_sub=None):
    """partes: [(rótulo, valor, cor)]. Legenda à direita com quantidade e percentual."""
    partes = [p for p in partes if p[1] > 0]
    total = sum(p[1] for p in partes)
    if not total:
        return None
    rotulo_w = max(len(p[0]) for p in partes) * 6.6 + 17 + 82  # rótulo + quantidade + percentual
    if h > w * 0.75 and w >= rotulo_w:  # bloco alto: rosca em cima, legenda embaixo
        return _rosca_vertical(partes, total, w, h, centro, centro_sub)
    raio = max(min(h / 2 - 6, w * 0.22, (w - rotulo_w - 24) / 2, 78), 24)
    esp = raio * 0.32
    cx, cy = max(raio + 6, (w - rotulo_w - 18) / 2 - raio * 0.2), h / 2
    circ = 2 * math.pi * (raio - esp / 2)
    corpo, acum = [], 0
    for rot, v, cor in partes:
        frac = v / total
        corpo.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{raio - esp / 2:.1f}" fill="none" stroke="{cor}" stroke-width="{esp:.1f}" '
                     f'stroke-dasharray="{circ * frac:.2f} {circ:.2f}" stroke-dashoffset="{-circ * acum:.2f}" '
                     f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>')
        acum += frac
    corpo.append(_txt(cx, cy + 5, centro if centro is not None else _n(total, 0), min(raio * 0.42, 24), TEXTO, 800))
    if centro_sub:
        corpo.append(_txt(cx, cy + 5 + min(raio * 0.3, 15), centro_sub, 9.5, SUAVE))
    xl = cx + raio + 18
    linha = min(22, (h - 10) / max(len(partes), 1))
    y0 = cy - linha * len(partes) / 2 + linha / 2
    for k, (rot, v, cor) in enumerate(partes):
        y = y0 + k * linha
        corpo.append(f'<rect x="{xl:.1f}" y="{y - 6:.1f}" width="11" height="11" rx="3" fill="{cor}"/>')
        corpo.append(_txt(xl + 17, y + 3.5, rot, 11, TEXTO, 600, "start"))
        corpo.append(_txt(w - 46, y + 3.5, _n(v, 0), 11, TEXTO, 700, "end"))
        corpo.append(_txt(w - 2, y + 3.5, _n(v / total * 100, 0) + "%", 10.5, SUAVE, ancora="end"))
    return _svg(w, h, "".join(corpo), "Distribuição: " + ", ".join(f"{r} {v}" for r, v, _ in partes))


def _rosca_vertical(partes, total, w, h, centro, centro_sub):
    linha_leg = 21
    leg_h = linha_leg * len(partes) + 6
    raio = max(min((h - leg_h - 14) / 2, w / 2 - 10, 92), 24)
    esp = raio * 0.3
    cx, cy = w / 2, raio + 4
    circ = 2 * math.pi * (raio - esp / 2)
    corpo, acum = [], 0
    for rot, v, cor in partes:
        frac = v / total
        corpo.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{raio - esp / 2:.1f}" fill="none" stroke="{cor}" stroke-width="{esp:.1f}" '
                     f'stroke-dasharray="{circ * frac:.2f} {circ:.2f}" stroke-dashoffset="{-circ * acum:.2f}" '
                     f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>')
        acum += frac
    corpo.append(_txt(cx, cy + 6, centro if centro is not None else _n(total, 0), min(raio * 0.42, 28), TEXTO, 800))
    if centro_sub:
        corpo.append(_txt(cx, cy + 6 + min(raio * 0.3, 16), centro_sub, 10, SUAVE))
    y0 = cy + raio + 18
    xl, xr = 8, w - 8
    for k, (rot, v, cor) in enumerate(partes):
        y = y0 + k * linha_leg
        corpo.append(f'<rect x="{xl}" y="{y - 6:.1f}" width="11" height="11" rx="3" fill="{cor}"/>')
        corpo.append(_txt(xl + 17, y + 3.5, rot, 11, TEXTO, 600, "start"))
        corpo.append(_txt(xr - 40, y + 3.5, _n(v, 0), 11, TEXTO, 700, "end"))
        corpo.append(_txt(xr, y + 3.5, _n(v / total * 100, 0) + "%", 10.5, SUAVE, ancora="end"))
    return _svg(w, min(h, y0 + len(partes) * linha_leg), "".join(corpo), "Distribuição: " + ", ".join(f"{r} {v}" for r, v, _ in partes))


# ---------------------------------------------------------------- linha
def linha(pontos, w, h, unidade="", cor="#12228E", casas=1, y_de_zero=False, maximo=None, rotular_todos=None):
    """pontos: [(rótulo do eixo, valor)] em ordem. Valor None vira um buraco na linha."""
    validos = [(i, v) for i, (_, v) in enumerate(pontos) if v is not None]
    if len(validos) < 2:
        return None
    h = min(h, 260)
    esq, dir_, topo, base = 14, 14, 20, h - 22
    valores = [v for _, v in validos]
    menor = 0 if y_de_zero else min(valores)
    maior = maximo if maximo is not None else max(valores)
    faixa = (maior - menor) or 1
    n = len(pontos)
    passo = (w - esq - dir_) / max(n - 1, 1)
    xy = {i: (esq + passo * i, base - (base - topo) * ((v - menor) / faixa) * 0.84 - 4) for i, v in validos}
    corpo = [f'<line x1="{esq}" y1="{base}" x2="{w - dir_}" y2="{base}" stroke="{GRADE}"/>']
    segmento = []
    for i, _ in validos:
        segmento.append(f"{xy[i][0]:.1f},{xy[i][1]:.1f}")
    corpo.append(f'<polyline fill="none" stroke="{cor}" stroke-width="2.4" stroke-linejoin="round" points="{" ".join(segmento)}"/>')
    rotular = rotular_todos if rotular_todos is not None else (n <= 8 and passo >= 40)
    for k, (i, v) in enumerate(validos):
        x, y = xy[i]
        corpo.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#fff" stroke="{cor}" stroke-width="2"/>')
        if rotular or k in (0, len(validos) - 1):
            ancora = "start" if i == 0 else "end" if i == n - 1 else "middle"
            corpo.append(_txt(x, y - 8, _n(v, casas) + ("%" if unidade == "%" else ""), 10.5, cor, 700, ancora,
                              'paint-order="stroke" stroke="#fff" stroke-width="3"'))
    a_cada = max(1, math.ceil(52 / max(passo, 1)))
    for i, (rot, _) in enumerate(pontos):
        if i in (0, n - 1) or (i % a_cada == 0 and (n - 1 - i) >= a_cada):
            ancora = "start" if i == 0 else "end" if i == n - 1 else "middle"
            corpo.append(_txt(esq + passo * i, base + 15, rot, 9.5, SUAVE, ancora=ancora))
    return _svg(w, h, "".join(corpo), "Linha: " + ", ".join(f"{r} {_n(v)}" for r, v in pontos if v is not None))


# ---------------------------------------------------------------- calendário do mês
def calendario(ano, mes, status_por_dia, cores, w, h):
    semanas = calendar.Calendar(firstweekday=0).monthdayscalendar(ano, mes)
    cab = 16
    cel_w, cel_h = w / 7, (h - cab) / len(semanas)
    corpo = [_txt(cel_w * i + cel_w / 2, 11, d, 9.5, SUAVE, 600) for i, d in enumerate(["seg", "ter", "qua", "qui", "sex", "sáb", "dom"])]
    for r, semana in enumerate(semanas):
        for c, dia in enumerate(semana):
            if not dia:
                continue
            x, y = c * cel_w + 2, cab + r * cel_h + 2
            st = status_por_dia.get(dia)
            fundo = cores.get(st, "#f6f8fb")
            corpo.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cel_w - 4:.1f}" height="{cel_h - 4:.1f}" rx="5" fill="{fundo}"/>')
            corpo.append(_txt(x + (cel_w - 4) / 2, y + (cel_h - 4) / 2 + 4, dia, 10.5,
                              "#fff" if st in ("presente", "falta") else TEXTO, 700 if st else 400))
    return _svg(w, h, "".join(corpo), f"Calendário de {mes}/{ano}")
