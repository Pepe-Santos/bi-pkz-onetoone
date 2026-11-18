"""Páginas dos relatórios v2: o que vai em cada folha e em que tamanho.

Cada folha A4 tem um corpo fixo dividido em linhas; cada linha, em blocos de 1 a 12 colunas.
O tamanho de cada bloco é conhecido antes de desenhar, então os gráficos nascem no tamanho
certo e a quantidade de folhas é sempre a mesma: 3 (semanal), 4 (mensal) e 5 (anual).

Bloco sem dado vira um painel que diz o que falta e por quê. Nunca entra número inventado.
"""
import math
from pathlib import Path

from . import graficos as G
from . import indicadores as I
from .contrato import ler_data

# Geometria da folha A4 em px (96 dpi)
LARGURA, ALTURA = 794, 1123
CABECALHO, RODAPE = 72, 38
MARGEM_X, MARGEM_Y, ESPACO = 26, 14, 10
CORPO_L = LARGURA - 2 * MARGEM_X
CORPO_A = ALTURA - CABECALHO - RODAPE - 2 * MARGEM_Y
PAD = 12

COR = {"presente": "#157a4b", "falta": "#be123c", "cancelado": "#94a3b8", "agendado": "#9db2d8"}
ROTULO_STATUS = {"presente": "Presença", "falta": "Falta", "cancelado": "Cancelada", "agendado": "Agendada"}
SITUACAO = {"melhorou": ("Melhorou", "#157a4b"), "piorou": ("Piorou", "#be123c"), "estavel": ("Estável", "#64748b"),
            "em_validacao": ("Regra em validação", "#b45309"), "sem_comparacao": ("Primeira medição", "#64748b"),
            "sem_classificacao": ("Sem direção definida", "#64748b")}
TEMAS = {
    "PKZ": {"nome": "PKZ", "marca": "Playmakerz Lab", "subtitulo": "Acompanhamento esportivo · para pais e responsáveis",
            "primaria": "#12228E", "escura": "#0e1a6b", "destaque": "#c2f24a", "suave": "#eef1fb", "linha": "#dbe0f0",
            "rodape": "Juntos, desenvolvendo atletas e construindo confiança."},
    "ONE_TO_ONE": {"nome": "One to One", "marca": "One to One Studio", "subtitulo": "Acompanhamento individual do aluno",
                   "primaria": "#12228E", "escura": "#0e1a6b", "destaque": "#c2f24a", "suave": "#eef1fb", "linha": "#dbe0f0",  # mesma paleta da PKZ
                   "rodape": "Treino individualizado para jovens adultos e adultos."},
}
TITULOS = {"semanal": "Relatório da semana", "mensal": "Relatório do mês", "anual": "Relatório do ano"}
NO_PERIODO = {"semanal": "na semana", "mensal": "no mês", "anual": "no ano"}
DO_PERIODO = {"semanal": "da semana", "mensal": "do mês", "anual": "do ano"}


# ---------------------------------------------------------------- blocos
def bloco(tipo, span=12, **campos):
    return {"tipo": tipo, "span": span, **campos}


def grafico(titulo, desenhar, span=12, sub=None, legenda=None, nota=None, sem_dados=None, maximo=None, minimo=None):
    """desenhar(w, h) -> SVG, ou None quando não há dado: o bloco vira painel explicativo.

    minimo e maximo: alturas do bloco em px entre as quais o gráfico continua legível e sem sobra
    (sem eles, valem os padrões de _altura_minima e _altura_maxima)."""
    return bloco("grafico", span, titulo=titulo, sub=sub, desenhar=desenhar, legenda=legenda or [], nota=nota,
                 sem_dados=sem_dados or "Sem dados suficientes para este gráfico no período.", maximo=maximo, minimo=minimo)


ROSCA = {"minimo": 230, "maximo": 300}  # menor que isso a legenda aperta; maior, só ocupa espaço


def _barras_h(n, extra=0):
    """Barras horizontais: cabeçalho e nota, mais uma faixa por item (18 px no mínimo, 30 px no máximo)."""
    base = 2 * PAD + 60 + 30 + extra
    return {"minimo": base + 18 * max(n, 2), "maximo": base + 30 * max(n, 2)}


def sem_dados(titulo, texto, span=12, sub=None):
    return bloco("sem_dados", span, titulo=titulo, sub=sub, texto=texto)


def _linhas_texto(texto, largura, px=6.2):
    return max(1, math.ceil(len(texto or "") * px / max(largura, 1))) if texto else 0


def _vazio(b):
    if b["tipo"] == "sem_dados":
        return True
    if b["tipo"] == "grafico":
        return b["desenhar"] is None or b["desenhar"](480, 220) is None
    return b["tipo"] == "mini" and not b["itens"]


def _natural(b, largura):
    """Altura que um bloco de texto realmente usa; None para blocos que crescem (gráficos, tabelas)."""
    iw = largura - 2 * PAD
    cab = 24 + 15 * _linhas_texto(b.get("sub"), iw, 5.9) if b.get("titulo") else 0
    if _vazio(b):
        return 2 * PAD + cab + 15 * _linhas_texto(b.get("texto") or b.get("sem_dados"), iw - 40, 6.3) + 14
    if b["tipo"] == "lista":
        itens = b["itens"] or [("", b.get("vazio") or "")]
        return 2 * PAD + cab + sum(19 + 14.5 * min(2, _linhas_texto(d, iw - 12, 5.8)) + 6 for _, d in itens) + 10
    if b["tipo"] == "texto":
        return 2 * PAD + cab + sum(17 * _linhas_texto(p, iw, 6.3) + 5 for p in b["paragrafos"]) + 4
    if b["tipo"] == "tabela":
        linhas = len(b["linhas"])
        return min(2 * PAD + cab + 26 + linhas * (b.get("altura_linha") or 22) + 18 + (16 if b.get("nota") else 0) + 4, CORPO_A * 0.5)
    if b["tipo"] == "kpis" and b.get("titulo"):
        return 2 * PAD + 24 + 110
    if b["tipo"] == "criterios":
        pares = [b["itens"][i:i + 2] for i in range(0, len(b["itens"]), 2)]
        return 2 * PAD + cab + sum(max(14.5 * _linhas_texto(f"{t}: {d}", iw / 2 - 8, 5.5) for t, d in par) + 5 for par in pares) + 4
    return None


def _tabela_completa(b):
    """Altura da tabela com todas as linhas (sem o limite de meia folha de _natural)."""
    cab = 24 + 15 * _linhas_texto(b.get("sub"), b.get("w", CORPO_L) - 2 * PAD, 5.9) if b.get("titulo") else 0
    return 2 * PAD + cab + 26 + len(b["linhas"]) * (b.get("altura_linha") or 22) + 18 + (16 if b.get("nota") else 0) + 4


ENCOLHEM = ("tabela", "lista", "comparacoes")


def _caber(pagina):
    """Se as linhas de altura natural não cabem na folha, encolhe as que têm tabela ou lista.

    Tabela e lista cortam o que sobra com uma nota (+N registros); texto e gráfico não encolhem.
    Cada linha que cresce (gráficos) fica com pelo menos 120 px.
    """
    linhas = pagina["linhas"]
    fixas = [l for l in linhas if isinstance(l["altura"], int)]
    excesso = sum(l["altura"] for l in fixas) + ESPACO * (len(linhas) - 1) + 120 * (len(linhas) - len(fixas)) - CORPO_A
    while excesso > 0:
        candidatas = [l for l in fixas if any(b["tipo"] in ENCOLHEM for b in l["blocos"]) and l["altura"] > 110]
        if not candidatas:
            break
        l = max(candidatas, key=lambda x: x["altura"])
        corte = min(excesso, l["altura"] - 110)
        l["altura"] -= int(math.ceil(corte))
        excesso -= corte


MINIMO_GRAFICO = 150  # altura mínima de uma linha com gráfico ao juntar páginas; com espaço sobrando, ele cresce


def _sem_vazios(paginas):
    """Tira os blocos sem dado. Linha que fica vazia sai; bloco que fica sozinho ocupa a linha toda."""
    for pagina in paginas:
        linhas = []
        for l in pagina["linhas"]:
            blocos = [b for b in l["blocos"] if not _vazio(b) and not (b["tipo"] == "lista" and not b["itens"])]
            if blocos:
                linhas.append({**l, "blocos": blocos})
        pagina["linhas"] = linhas
    return [p for p in paginas if p["linhas"]]


def _minimo_bloco(b, largura):
    """Menor altura em que o bloco continua legível (tabela: com todas as linhas, até 60% da folha)."""
    natural = _natural(b, largura)
    if b["tipo"] == "tabela":
        return max(natural, min(_tabela_completa(b), CORPO_A * 0.6))
    if natural is not None:
        return natural
    if b["tipo"] == "comparacoes":
        return min(2 * PAD + 44 + math.ceil(len(b["itens"]) / (2 if b.get("colunas_duplas") else 1)) * 44, CORPO_A * 0.5)
    if b["tipo"] == "grafico":
        return min(max(MINIMO_GRAFICO, b.get("minimo") or 0), CORPO_A * 0.6)
    if b["tipo"] == "mini":  # até 2 fileiras de minigráficos; o resto vira "Mostrando X de N"
        n = len(b["itens"])
        fileiras = min(2, math.ceil(n / min(n, b.get("colunas", 4)))) if n else 1
        return 2 * PAD + 24 + 15 * _linhas_texto(b.get("sub"), largura - 2 * PAD, 5.9) + fileiras * 150 + 4
    return MINIMO_GRAFICO


def _larguras(l):
    n = len(l["blocos"])
    return [(CORPO_L - ESPACO * (n - 1)) * b["span"] / sum(x["span"] for x in l["blocos"]) for b in l["blocos"]]


def _altura_minima(l):
    if isinstance(l["altura"], int):
        # tabela conta com todas as linhas (até 60% da folha), para não esconder registros ao juntar folhas
        tabelas = [min(_tabela_completa(b), CORPO_A * 0.6) for b in l["blocos"] if b["tipo"] == "tabela"]
        return max([l["altura"]] + tabelas)
    return max(_minimo_bloco(b, w) for b, w in zip(l["blocos"], _larguras(l)))


def _altura_maxima(b, largura):
    """Até onde um bloco pode crescer sem virar espaço vazio. None = sem limite."""
    natural = _natural(b, largura)
    if natural is not None:
        return natural
    if b["tipo"] == "grafico":
        return b.get("maximo") or (440 if largura > CORPO_L * 0.7 else 420)
    if b["tipo"] == "mini":
        n = len(b["itens"])
        fileiras = math.ceil(n / min(n, b.get("colunas", 4))) if n else 1
        return 2 * PAD + 24 + 15 * _linhas_texto(b.get("sub"), largura - 2 * PAD, 5.9) + fileiras * 175 + 24
    if b["tipo"] == "comparacoes":
        return 2 * PAD + 60 + math.ceil(len(b["itens"]) / (2 if b.get("colunas_duplas") else 1)) * 44 + 30
    return None


def _maxima_da_linha(l):
    n = len(l["blocos"])
    larguras = [(CORPO_L - ESPACO * (n - 1)) * b["span"] / sum(x["span"] for x in l["blocos"]) for b in l["blocos"]]
    maximos = [_altura_maxima(b, w) for b, w in zip(l["blocos"], larguras)]
    return None if any(m is None for m in maximos) else math.ceil(max(maximos))


def _maxima_total(l):
    """Até onde a linha pode crescer na folha (tabela com todas as linhas, gráfico até o teto)."""
    tabelas = [_tabela_completa(b) for b in l["blocos"] if b["tipo"] == "tabela"]
    if isinstance(l["altura"], int):
        return max([l["altura"]] + tabelas)
    m = _maxima_da_linha(l)
    return math.inf if m is None else max([m] + tabelas)


def _quebras(linhas, maximo_de_folhas):
    """Divide as linhas (na ordem) em até maximo_de_folhas folhas com o mínimo de espaço em branco.

    Espaço em branco de uma folha = o que sobra mesmo com cada linha no seu tamanho máximo.
    A folha de conclusão (a última) pesa 8 vezes mais e a primeira, 3; uma folha nunca recebe mais que o mínimo cabível.
    Devolve (grupos, custo).
    """
    n = len(linhas)
    minimos = [_altura_minima(l) for l in linhas]
    maximos = [_maxima_total(l) for l in linhas]

    def custo(i, j):  # folha com as linhas i..j-1
        k = j - i
        if sum(minimos[i:j]) + ESPACO * (k - 1) > CORPO_A and k > 1:
            return None
        cresce = sum(maximos[i:j])
        if j == n:  # na conclusão os blocos ainda podem crescer um pouco (até 10%) para fechar a folha
            cresce = max(cresce, 1.1 * sum(minimos[i:j]))
        branco = max(0, CORPO_A - cresce - ESPACO * (k - 1))
        return branco ** 2 * (8 if j == n else 3 if i == 0 else 1)

    melhor = {(0, 0): (0, None)}  # (linhas usadas, folhas) -> (custo, corte anterior)
    for s in range(1, maximo_de_folhas + 1):
        for j in range(1, n + 1):
            opcoes = []
            for i in range(j):
                if (i, s - 1) in melhor and (c := custo(i, j)) is not None:
                    opcoes.append((melhor[(i, s - 1)][0] + c, i))
            if opcoes:
                melhor[(j, s)] = min(opcoes)
    possiveis = [s for s in range(1, maximo_de_folhas + 1) if (n, s) in melhor]
    if not possiveis:  # não cabe no máximo de folhas
        return None, math.inf
    s = min(possiveis, key=lambda s: (melhor[(n, s)][0], s))
    custo_total = melhor[(n, s)][0]
    grupos, j = [], n
    while s:
        i = melhor[(j, s)][1]
        grupos.insert(0, linhas[i:j])
        j, s = i, s - 1
    return grupos, custo_total


def _reagrupar(paginas):
    """Junta páginas que ficaram com pouco conteúdo: as linhas seguem na mesma ordem e cada
    folha recebe o que cabe nela. O título da folha junta os títulos das partes que ela tem."""
    fila = [(i, pagina["titulo"], l) for i, pagina in enumerate(paginas) for l in pagina["linhas"]]
    ultima = len(paginas) - 1  # o fechamento (conclusão, como ler) fica sempre no fim, na ordem
    folhas, atual, usado = [], None, 0

    def precisa(item):
        return _altura_minima(item[2]) + (ESPACO if atual["linhas"] else 0)

    def colocar(item):
        nonlocal usado
        usado += precisa(item)
        if item[1] not in atual["titulos"]:
            atual["titulos"].append(item[1])
        atual["linhas"].append(item[2])

    while fila:
        if atual is not None and usado + precisa(fila[0]) <= CORPO_A:
            colocar(fila.pop(0))
            continue
        # A próxima linha não cabe. Antes de abrir outra folha, traz a primeira linha da mesma página
        # ou da seguinte (nunca do fechamento) que caiba no espaço livre, para a folha não ficar com
        # um bloco esticado.
        if atual is not None and CORPO_A - usado >= MINIMO_GRAFICO:
            origem = fila[0][0]
            k = next((k for k, item in enumerate(fila) if item[0] in (origem, origem + 1) and item[0] < ultima
                      and usado + precisa(item) <= CORPO_A), None)
            if k is not None:
                colocar(fila.pop(k))
                continue
        atual = {"titulos": [], "linhas": []}
        folhas.append(atual)
        usado = 0
        colocar(fila.pop(0))
    if len(folhas) > len(paginas):  # muito conteúdo: fica a divisão original, que já cabe no máximo de folhas
        return paginas
    # A ordem acima fica; as quebras entre folhas são escolhidas de novo para deixar o mínimo de
    # espaço em branco, sobretudo na folha de conclusão (a última).
    origem = {id(l): titulo for _, titulo, l in [(i, p["titulo"], l) for i, p in enumerate(paginas) for l in p["linhas"]]}
    ordem = [l for f in folhas for l in f["linhas"]]
    grupos, custo = _quebras(ordem, len(paginas))
    if grupos is None:
        return paginas
    # Se a folha de conclusão ainda fica com espaço, ela pode receber uma parte com gráfico de uma folha
    # anterior (nunca da primeira): fica antes da conclusão, e vale a troca que deixar menos espaço em branco.
    fechamento = [l for l in ordem if origem[id(l)] == paginas[-1]["titulo"]]
    inicio = ordem.index(fechamento[0]) if fechamento else len(ordem)
    primeira = {id(l) for l in grupos[0]}
    for l in ordem[:inicio]:
        if id(l) in primeira or not any(b["tipo"] in ("grafico", "mini") for b in l["blocos"]):
            continue
        nova = [x for x in ordem if x is not l]
        nova.insert(nova.index(fechamento[0]) if fechamento else len(nova), l)
        g, c = _quebras(nova, len(paginas))
        if g is not None and c < custo * 0.5:
            grupos, custo = g, c
    folhas = [{"linhas": grupo} for grupo in grupos]
    for f in folhas:
        f["titulos"] = list(dict.fromkeys(origem[id(l)] for l in f["linhas"]))
    usados = set()
    for f in folhas:
        juntos = " e ".join(f["titulos"][:2])
        f["titulo"] = juntos if len(juntos) <= 34 else f["titulos"][0]  # título longo quebraria o cabeçalho
        if f["titulo"] in usados:  # título que já apareceu: usa o de outra parte da folha, se houver
            f["titulo"] = next((x for x in f["titulos"] if x not in usados and len(x) <= 34), f["titulo"])
        usados.add(f["titulo"])
    return folhas


def montar(paginas):
    """Tira os blocos sem dado, junta as páginas que ficaram vazias e calcula o tamanho de cada bloco.

    Linhas de texto e tabelas ficam com a altura que usam; o resto da folha vai para os gráficos.
    O relatório termina com até 3, 4 ou 5 folhas (semanal, mensal, anual), menos quando falta dado.
    """
    paginas = _reagrupar(_sem_vazios(paginas))
    for pagina in paginas:
        for l in pagina["linhas"]:
            if isinstance(l["altura"], float):
                n = len(l["blocos"])
                larguras = [(CORPO_L - ESPACO * (n - 1)) * b["span"] / sum(x["span"] for x in l["blocos"]) for b in l["blocos"]]
                naturais = [_natural(b, w) for b, w in zip(l["blocos"], larguras)]
                if all(x is not None for x in naturais):
                    l["altura"] = max(80, math.ceil(max(naturais)))
        _caber(pagina)
        # Sem gráfico para crescer, a folha termina onde termina o conteúdo (o rodapé fica embaixo).
        fixas = sum(l["altura"] for l in pagina["linhas"] if isinstance(l["altura"], int))
        flex = [l for l in pagina["linhas"] if isinstance(l["altura"], float)]
        livre = CORPO_A - ESPACO * (len(pagina["linhas"]) - 1) - fixas
        for l in flex:  # menor altura que a linha aceita: a do maior bloco dela (texto, tabela ou gráfico legível)
            l["minimo"] = _altura_minima(l)
        presas = []
        while True:
            soltas = [l for l in flex if l not in presas]
            pesos = sum(l["altura"] for l in soltas) or 1
            resto = livre - sum(l["minimo"] for l in presas)
            nova = [l for l in soltas if resto * l["altura"] / pesos < l["minimo"]]
            if not nova:
                break
            presas += nova
        if presas and resto < 0:  # nem os mínimos cabem: as linhas presas dividem o que há
            total = sum(l["minimo"] for l in presas) or 1
            for l in presas:
                l["minimo"] = l["minimo"] * (livre - 110 * len(soltas)) / total
            resto = livre - sum(l["minimo"] for l in presas)
        for l in presas:
            l["px"] = math.floor(l["minimo"])
        for l in soltas:
            l["px"] = math.floor(resto * l["altura"] / pesos)
        # Nenhuma linha cresce além do que o conteúdo aproveita (ex.: uma rosca sozinha numa linha inteira).
        # O que sobra vai para as linhas que ainda podem crescer; se nenhuma pode, a folha termina antes.
        for _ in range(len(flex)):
            limitadas = [l for l in flex if not l.get("teto") and (m := _maxima_da_linha(l)) is not None and l["px"] > max(m, l["minimo"])]
            if not limitadas:
                break
            sobra = 0
            for l in limitadas:
                novo = math.floor(max(_maxima_da_linha(l), l["minimo"]))
                sobra += l["px"] - novo
                l["px"], l["teto"] = novo, True
            podem = [l for l in flex if not l.get("teto")]
            peso = sum(l["px"] for l in podem) or 1
            for l in podem:
                l["px"] += math.floor(sobra * l["px"] / peso)
        for l in pagina["linhas"]:
            if isinstance(l["altura"], int):
                l["px"] = l["altura"]
        # Com espaço sobrando na folha, a tabela que escondia linhas ("+N registros") cresce para mostrá-las.
        livre = CORPO_A - sum(l["px"] for l in pagina["linhas"]) - ESPACO * (len(pagina["linhas"]) - 1)
        for l in pagina["linhas"]:
            completas = [_tabela_completa(b) for b in l["blocos"] if b["tipo"] == "tabela"]
            if livre > 0 and completas and max(completas) > l["px"]:
                ganho = min(livre, math.ceil(max(completas)) - l["px"])
                l["px"] += ganho
                livre -= ganho
        if pagina is paginas[-1] and livre > 0:  # folha de conclusão: sem espaço em branco embaixo
            # só crescem as linhas de texto, lista e tabela: gráfico esticado é o que se quer evitar
            textuais = [l for l in pagina["linhas"] if not any(b["tipo"] in ("grafico", "mini", "comparacoes") for b in l["blocos"])]
            alvo = textuais or pagina["linhas"]
            total = sum(l["px"] for l in alvo) or 1
            for l in alvo:
                antes = l["px"]
                l["px"] += math.floor(livre * l["px"] / total)
                # texto, listas e "Como ler" ampliam a letra (até 30%) e espalham o conteúdo na altura nova
                escala = round(min(1.3, (l["px"] - 2 * PAD) / max(antes - 2 * PAD, 1) * 0.9), 2)
                for b in l["blocos"]:
                    if b["tipo"] in ("lista", "texto", "criterios") and escala > 1.02:
                        b["escala"] = escala
        for l in pagina["linhas"]:
            n = len(l["blocos"])
            for b in l["blocos"]:
                b["w"] = (CORPO_L - ESPACO * (n - 1)) * b["span"] / sum(x["span"] for x in l["blocos"])
                b["h"] = l["px"]
                _preparar(b)
    return paginas


def _preparar(b):
    for campo in ("titulo", "sub", "nota", "colunas_duplas", "altura_linha", "svg", "compacta", "escala"):
        b.setdefault(campo, None)
    b.setdefault("legenda", [])
    iw, ih = b["w"] - 2 * PAD, b["h"] - 2 * PAD
    cab = (18 if b.get("titulo") else 0) + 15 * _linhas_texto(b.get("sub"), iw, 5.9) + (6 if b.get("titulo") else 0)
    b["iw"], b["ih"] = iw, ih
    if b["tipo"] == "grafico":
        rod = (20 if b["legenda"] else 0) + 14 * _linhas_texto(b.get("nota"), iw, 5.6)
        area_h = ih - cab - rod
        svg = b["desenhar"](iw, area_h) if b["desenhar"] else None
        if svg:
            b["svg"] = svg
        else:
            b["tipo"], b["texto"], b["sub"] = "sem_dados", b["sem_dados"], None
    elif b["tipo"] == "lista" and b["itens"]:
        usado, cabem = cab + 4, 0
        for _, d in b["itens"]:
            usado += 19 + 14.5 * min(2, _linhas_texto(d, iw - 12, 5.8)) + 6
            if usado > ih + 4:
                break
            cabem += 1
        if cabem < len(b["itens"]):
            sobra = len(b["itens"]) - cabem
            b["itens"] = b["itens"][:max(cabem, 1)]
            b["nota"] = f"+{sobra} {'item' if sobra == 1 else 'itens'} além dos mostrados."
    elif b["tipo"] in ("tabela", "comparacoes"):
        alt = {"tabela": b.get("altura_linha") or 22, "comparacoes": 44}[b["tipo"]]
        cabeca = 26 if b["tipo"] == "tabela" else 0
        cabem = max(1, int((ih - cab - cabeca - 18) // alt))
        itens = b["linhas"] if b["tipo"] == "tabela" else b["itens"]
        if b["tipo"] == "comparacoes" and b.get("colunas_duplas"):
            cabem *= 2
        if len(itens) > cabem:
            sobra = len(itens) - cabem
            if b["tipo"] == "tabela":
                b["linhas"] = itens[:cabem]
            else:
                b["itens"] = itens[:cabem]
            b["nota"] = (b.get("nota") + " " if b.get("nota") else "") + f"+{sobra} {'registro' if sobra == 1 else 'registros'} além dos mostrados ({b.get('onde_resto') or 'não cabem nesta página'})."
    elif b["tipo"] == "mini":
        n = len(b["itens"])
        if not n:
            b["tipo"], b["texto"], b["sub"] = "sem_dados", b["sem_dados"], None
            return
        colunas = min(n, b.get("colunas", 4))
        fileiras = min(math.ceil(n / colunas), max(1, int((ih - cab) // 150)))
        if n > colunas * fileiras:
            b["nota"] = f"Mostrando {colunas * fileiras} de {n} testes com duas ou mais medições."
            b["itens"] = b["itens"][:colunas * fileiras]
        cw = (iw - 8 * (colunas - 1)) / colunas
        ch = (ih - cab - 8 * (fileiras - 1) - (18 if b.get("nota") else 0) - 4) / fileiras
        for it in b["itens"]:
            it["w"], it["h"] = cw, ch
            it["svg"] = it["desenhar"](cw - 16, min(ch - 44, 120))
        b["colunas"] = colunas


# ---------------------------------------------------------------- peças comuns
def nome_curto(ind):
    partes = (ind["aluno"]["nome"] or "").split()
    return partes[0] if partes else "O aluno"


def identificacao(ind, tema):
    a = ind["aluno"]
    detalhes = []
    if a.get("idade") is not None:
        detalhes.append(f"{a['idade']} anos")
    if a.get("categoria"):
        detalhes.append(a["categoria"].replace("_", " ").capitalize())
    if a.get("modalidade"):
        detalhes.append(a["modalidade"])
    if a.get("clube"):
        detalhes.append(a["clube"])
    if a.get("turno"):
        detalhes.append(f"turno {a['turno'].lower()}")
    iniciais = "".join(p[0] for p in (a["nome"] or "?").split()[:1] + (a["nome"] or "?").split()[-1:]).upper()
    if ind["modalidade"] == "PKZ":
        chave, valor = "Avaliações físicas até o fim do período", str(len(ind["avaliacoes_todas"]))
    else:
        chave, valor = "Relatórios de treino no período", str(ind["treinos"])
    return bloco("ident", 12, nome=a["nome"], iniciais=iniciais, detalhes=" · ".join(detalhes) or "Dados de cadastro não informados",
                 periodo=f"{ind['inicio']:%d/%m/%Y} a {ind['fim']:%d/%m/%Y}", chave=chave, valor=valor)


def cartao_atleta(ind, span=5):
    """O cartão do atleta: foto, nota ("over"), nível e os atributos (One to One sem testes: acompanhamento)."""
    a, s = ind["aluno"], ind["sessoes"]
    partes = [x for x in (a.get("modalidade") if ind["modalidade"] == "PKZ" else "One to One",
                          (a.get("categoria") or "").replace("_", " ").capitalize() or None,
                          f"{a['idade']} anos" if a.get("idade") is not None else None) if x]
    iniciais = "".join(p[0] for p in (a["nome"] or "?").split()[:1] + (a["nome"] or "?").split()[-1:]).upper()
    foto = None
    if a.get("foto"):
        import base64
        import mimetypes
        caminho = Path(a["foto"])
        foto = f"data:{mimetypes.guess_type(caminho.name)[0] or 'image/jpeg'};base64,{base64.b64encode(caminho.read_bytes()).decode()}"
    base = {"nome": a["nome"], "detalhes": " · ".join(partes), "iniciais": iniciais, "foto": foto,
            "foto_ilustrativa": a.get("foto_ilustrativa")}
    if ind["modalidade"] == "PKZ" or ind["cartao"].get("origem") == "fisico":
        k = ind["cartao"]
        return bloco("cartao", span, **base, numero=str(k["nota"]) if k["nota"] is not None else "—",
                     legenda=k["rotulo"], nivel=k["nivel"], metal=k["metal"],
                     atributos=[{"sigla": x["sigla"], "valor": "—" if x["valor"] is None else str(x["valor"]), "alerta": x["alerta"],
                                 "titulo": x["nome"]} for x in k["atributos"]],
                     nota_rodape=("Nota provisória: média dos atributos, cada um a posição entre "
                                  f"{k['colegas']} colegas da mesma faixa de idade." if k["nota"] is not None else
                                  f"A nota aparece com {k['minimo_para_nota']} ou mais atributos calculados."))
    k = ind["cartao"]
    return bloco("cartao", span, **base, numero=str(k["nota"]) if k["nota"] is not None else "—",
                 legenda="Nota", nivel=k["nivel"], metal=k["metal"],
                 atributos=[{"sigla": x["sigla"], "valor": str(x["valor"]), "alerta": x["alerta"], "titulo": x["nome"]} for x in k["atributos"]],
                 nota_rodape=("Nota provisória (0 a 100): média dos atributos de acompanhamento, até haver testes físicos."
                              if k["nota"] is not None else
                              f"A nota aparece com {k['minimo_para_nota']} ou mais atributos calculados no período."))


def kpis(ind):
    s, tem = ind["sessoes"], bool(ind["sessoes_lista"])
    if not tem:
        itens = []  # sem sessão no período: o quadro mostra só o que existe
        if ind["modalidade"] == "PKZ":
            c = ind["contagem_situacao"]
            itens += [{"valor": str(len(ind["avaliacoes_periodo"])), "rotulo": "Avaliações físicas", "nota": NO_PERIODO[ind["tipo"]], "cor": "primaria"},
                      {"valor": str(ind["resultados_periodo"]), "rotulo": "Resultados", "nota": "registrados no período", "cor": "primaria"},
                      {"valor": str(c["melhorou"]), "rotulo": "Melhoraram", "nota": "contra a medição anterior", "cor": "verde"},
                      {"valor": str(c["piorou"]), "rotulo": "Pioraram", "nota": "contra a medição anterior", "cor": "vermelho" if c["piorou"] else "texto"},
                      {"valor": str(c["em_validacao"]), "rotulo": "Regra em validação", "nota": "sem classificar", "cor": "texto"}]
        else:
            d = ind["dist"]
            itens += [{"valor": str(ind["treinos"]), "rotulo": "Treinos registrados", "nota": "relatórios do professor", "cor": "primaria"},
                      {"valor": str(d["intensidade"]["preenchidos"]), "rotulo": "Com intensidade", "nota": "registrada", "cor": "texto"},
                      {"valor": str(d["desempenho"]["preenchidos"]), "rotulo": "Com desempenho", "nota": "registrado", "cor": "texto"}]
        return bloco("kpis", 12, itens=itens)

    def v(n):
        return str(n)
    itens = [
        {"valor": v(s["total"]), "rotulo": "Sessões agendadas", "nota": "todas as situações", "cor": "texto"},
        {"valor": v(s["presentes"]), "rotulo": "Presenças", "nota": "chamada registrada", "cor": "verde"},
        {"valor": v(s["faltas"]), "rotulo": "Faltas", "nota": "chamada registrada", "cor": "vermelho" if s["faltas"] else "texto"},
        {"valor": v(s["cancelados"]), "rotulo": "Cancelamentos", "nota": "não contam como falta", "cor": "texto"},
        {"valor": v(s["agendados"]), "rotulo": "Agendadas", "nota": (f"{s['pendentes']} sem chamada" if s["pendentes"] else "ainda vão acontecer") if tem else "—", "cor": "texto"},
        {"valor": I.pct(s["frequencia"]) if s["frequencia"] is not None else I.SEM_REGISTRO, "rotulo": "Frequência",
         "nota": "presenças ÷ (presenças + faltas)", "cor": "primaria"},
    ]
    if ind["modalidade"] == "PKZ":
        n = len(ind["avaliacoes_periodo"])
        itens.append({"valor": str(n), "rotulo": "Avaliações físicas", "nota": f"{ind['resultados_periodo']} resultados" if n else NO_PERIODO[ind['tipo']], "cor": "primaria"})
    else:
        itens.append({"valor": str(ind["treinos"]), "rotulo": "Treinos registrados", "nota": "relatórios do professor", "cor": "primaria"})
    return bloco("kpis", 12, itens=itens)


def resumo(ind, span=7):
    s, nome = ind["sessoes"], nome_curto(ind)
    if s["base"]:
        frase = [(f"{nome} compareceu a ", False), (f"{s['presentes']} de {s['base']}", True),
                 (f" {'sessão' if s['base'] == 1 else 'sessões'} com chamada {NO_PERIODO[ind['tipo']]}", False)]
    elif ind["modalidade"] == "PKZ" and ind["avaliacoes_periodo"]:
        frase = [(f"{nome} fez ", False), (I.plural(len(ind["avaliacoes_periodo"]), "avaliação física", "avaliações físicas"), True),
                 (f" {NO_PERIODO[ind['tipo']]}", False)]
    elif s["total"]:
        frase = [(I.plural(s["total"], "sessão agendada", "sessões agendadas"), True), (f" {NO_PERIODO[ind['tipo']]}, ainda sem chamada registrada", False)]
    else:
        frase = [(f"Sem sessões registradas {NO_PERIODO[ind['tipo']]}", False)]
    itens = []
    ev = ind.get("evolucao_nota")
    if ev:
        de, para = ev["de"], ev["para"]
        mudou = "subiu" if para["nota"] > de["nota"] else "caiu" if para["nota"] < de["nota"] else "ficou igual"
        itens.append(f"Nota provisória {mudou}: {de['nota']} ({de['nivel']}, {de['metal'].lower()}) → {para['nota']} ({para['nivel']}, {para['metal'].lower()}).")
    if s["frequencia"] is not None:
        itens.append(f"Frequência de {I.pct(s['frequencia'])}: {I.plural(s['presentes'], 'presença', 'presenças')} e {I.plural(s['faltas'], 'falta', 'faltas')}.")
    if s["cancelados"]:
        itens.append(f"{I.plural(s['cancelados'], 'sessão cancelada', 'sessões canceladas')}, fora da conta da frequência.")
    if s["pendentes"]:
        itens.append(f"{I.plural(s['pendentes'], 'sessão passada segue', 'sessões passadas seguem')} como agendada, sem chamada registrada.")
    if ind["modalidade"] == "PKZ":
        cont = ind["contagem_situacao"]
        if ind["base_situacao"]:
            partes = [f"{cont['melhorou']} melhoraram", f"{cont['estavel']} estáveis", f"{cont['piorou']} pioraram"]
            if cont["em_validacao"]:
                partes.append(f"{cont['em_validacao']} com a regra em validação (sem classificar)")
            if cont["sem_comparacao"]:
                partes.append(f"{cont['sem_comparacao']} medidos pela primeira vez")
            itens.append(f"Testes {'medidos no período' if ind['tipo'] != 'anual' else 'com 2 ou mais medições no ano'}: " + I.lista_texto(partes) + ".")
        elif not ind["avaliacoes_periodo"]:
            ult = ind["avaliacoes_todas"][-1] if ind["avaliacoes_todas"] else None
            itens.append(f"Nenhuma avaliação física {NO_PERIODO[ind['tipo']]}." + (f" A última foi em {ult:%d/%m/%Y}." if ult else ""))
        if ind["resultados_validacao"] and not ind["base_situacao"]:
            itens.append(f"{I.plural(ind['resultados_validacao'], 'resultado é', 'resultados são')} de testes com a regra ainda em validação pela PKZ.")
    else:
        intens = ind["dist"]["intensidade"]["itens"]
        if ind["treinos"]:
            itens.append(f"{I.plural(ind['treinos'], 'relatório de treino registrado', 'relatórios de treino registrados')} pelo professor.")
        if intens:
            itens.append(f"Intensidade mais registrada: {intens[0][0].lower()} ({I.plural(intens[0][1], 'treino', 'treinos')}).")
    if ind.get("ano_incompleto") and ind["cobertura"]:
        a, b = ind["cobertura"]
        itens.append(f"Registros de {a:%d/%m} a {b:%d/%m}: o ano ainda não está completo nos dados.")
    return bloco("resumo", span, titulo=f"Resumo {DO_PERIODO[ind['tipo']]}", frase=frase, itens=itens[:5])


def rosca_sessoes(ind, span=5, titulo="Como ficaram as sessões"):
    s = ind["sessoes"]
    partes = [("Presenças", s["presentes"], COR["presente"]), ("Faltas", s["faltas"], COR["falta"]),
              ("Cancelamentos", s["cancelados"], COR["cancelado"]), ("Agendadas", s["agendados"], COR["agendado"])]
    return grafico(titulo, lambda w, h: G.rosca(partes, w, h, centro=str(s["total"]), centro_sub="sessões"), span, **ROSCA,
                   sub="Todas as sessões agendadas no período, por situação.",
                   sem_dados="Nenhuma sessão agendada no período: não há distribuição para mostrar.")


def ao_lado_do_resumo(ind, pkz):
    if ind["sessoes_lista"]:
        return rosca_sessoes(ind)
    return situacao_testes(ind, 5) if pkz else distribuicao_oto(ind, "intensidade", "Intensidade dos treinos", 5)


def colunas_status(lista, rotulo="rotulo", sub=None):
    return [{"rotulo": x[rotulo], "sub": sub(x) if sub else None,
             "partes": [(x["presentes"], COR["presente"]), (x["faltas"], COR["falta"]), (x["cancelados"], COR["cancelado"]),
                        (x["agendados"], COR["agendado"])]} for x in lista]


LEGENDA_STATUS = [(COR["presente"], "presenças"), (COR["falta"], "faltas"), (COR["cancelado"], "cancelamentos"), (COR["agendado"], "agendadas")]


def criterios(ind, span=12):
    itens = [("Frequência", "presenças ÷ (presenças + faltas) × 100. Cancelamentos e sessões ainda agendadas não entram na conta."),
             ("Sem registro", "não existe informação no sistema para aquele indicador no período; não é o mesmo que zero.")]
    if ind["modalidade"] == "PKZ":
        itens += [("Variação", "(resultado atual − resultado anterior) ÷ anterior × 100. Cada teste é comparado só com a sua própria medição anterior."),
                  ("Melhorou / piorou", "considera a direção do teste: em tempo (sprint, agilidade), valor menor é melhor. Abaixo de 2% de diferença, o teste é estável."),
                  ("Regra em validação", "a PKZ ainda não validou a regra do teste (direção e unidade): o resultado aparece com os valores, sem dizer se melhorou ou piorou, e fica fora da posição no grupo."),
                  ("Posição no grupo", "percentil entre colegas da mesma faixa de idade, sem nomes, só com 5 ou mais colegas no mesmo teste.")]
    else:
        itens += [("Nota de acompanhamento", "média, de 0 a 100, de frequência, constância (semanas com presença), treinos registrados e intensidade registrada (leve 33, moderada 66, alta 100); sai com 2 ou mais desses atributos."),
                  ("Treinos registrados", "relatórios de treino finalizados pelo professor no período."),
                  ("Intensidade e desempenho", "como o professor registrou cada treino. Campo vazio no registro aparece como sem registro.")]
    return bloco("criterios", span, titulo="Como ler este relatório", itens=itens)


def comparacao_periodo_anterior(ind, span=6):
    ant, s = ind["anterior"], ind["sessoes"]
    nome = {"semanal": "Semana anterior", "mensal": "Mês anterior", "anual": "Ano anterior"}[ind["tipo"]]
    titulo = {"semanal": "Comparação com a semana anterior", "mensal": "Comparação com o mês anterior", "anual": "Comparação com o ano anterior"}[ind["tipo"]]
    if not ant:
        return sem_dados(titulo,
                         f"Sem registros de {ind['inicio'] and I.periodo_anterior(ind['tipo'], ind['inicio'])[0]:%d/%m/%Y} a "
                         f"{I.periodo_anterior(ind['tipo'], ind['inicio'])[1]:%d/%m/%Y}: não há com o que comparar.", span)
    a = ant["sessoes"]
    f = lambda v: I.pct(v) if v is not None else I.SEM_REGISTRO
    linhas = [["Frequência", f(a["frequencia"]), f(s["frequencia"])],
              ["Presenças", str(a["presentes"]), str(s["presentes"])],
              ["Faltas", str(a["faltas"]), str(s["faltas"])],
              ["Cancelamentos", str(a["cancelados"]), str(s["cancelados"])]]
    if ind["modalidade"] == "PKZ":
        linhas.append(["Avaliações físicas", str(ant["avaliacoes"]), str(len(ind["avaliacoes_periodo"]))])
    else:
        linhas.append(["Treinos registrados", str(ant["treinos"]), str(ind["treinos"])])
    return bloco("tabela", span, titulo=titulo,
                 sub=f"{nome}: {ant['inicio']:%d/%m} a {ant['fim']:%d/%m/%Y}.",
                 colunas=["Indicador", nome, "Este período"], linhas=linhas)


def listas_destaque(ind, span=6):
    d = ind["destaques"]
    return [bloco("lista", span, titulo="Pontos positivos", tom="positivo", itens=d["positivos"],
                  vazio="Nenhum ponto positivo pode ser afirmado com os registros deste período."),
            bloco("lista", span, titulo="Pontos de atenção", tom="atencao", itens=d["atencao"],
                  vazio="Nenhum ponto de atenção nos registros deste período.")]


def conclusao(ind, span=12):
    s, nome, p = ind["sessoes"], nome_curto(ind), NO_PERIODO[ind["tipo"]]
    frases = []
    if s["total"]:
        frases.append(f"{I.plural(s['total'], 'sessão agendada', 'sessões agendadas')} {p}: {s['presentes']} com presença, {s['faltas']} com falta, "
                      f"{s['cancelados']} canceladas e {s['agendados']} ainda como agendadas."
                      + (f" Frequência de {I.pct(s['frequencia'])}." if s["frequencia"] is not None else " Sem chamada suficiente para calcular a frequência."))
    else:
        frases.append(f"Nenhuma sessão registrada {p}.")
    if ind["modalidade"] == "PKZ":
        if ind["avaliacoes_periodo"]:
            c = ind["contagem_situacao"]
            frases.append(f"{I.plural(len(ind['avaliacoes_periodo']), 'avaliação física', 'avaliações físicas')} "
                          f"({lista_datas(ind['avaliacoes_periodo'])}): {c['melhorou']} testes melhoraram, {c['estavel']} ficaram estáveis e {c['piorou']} pioraram"
                          + (f"; {I.plural(c['em_validacao'], 'teste tem', 'testes têm')} a regra em validação e não é classificado." if c["em_validacao"] else ".")
                          + (f" {I.plural(c['sem_comparacao'], 'teste foi medido', 'testes foram medidos')} pela primeira vez." if c["sem_comparacao"] else ""))
        else:
            frases.append(f"Sem avaliação física {p}; os resultados citados são da última avaliação registrada.")
        r = ind.get("reavaliacao")
        if r:
            vence = ler_data(r["vence_em"])
            frases.append(f"A reavaliação venceu em {vence:%d/%m/%Y}." if vence <= ind["fim"] else f"Próxima reavaliação até {vence:%d/%m/%Y} (regra provisória da PKZ: 90 dias).")
    else:
        if ind["treinos"]:
            intens = ind["dist"]["intensidade"]["itens"]
            frases.append(f"{I.plural(ind['treinos'], 'relatório de treino', 'relatórios de treino')} registrado(s)"
                          + (f", com intensidade mais frequente {intens[0][0].lower()}." if intens else "."))
        vazios = [n for c, n in (("tipo_treino", "tipo de treino"), ("objetivos", "objetivos")) if ind["treinos"] and not ind["dist"][c]["preenchidos"]]
        if vazios:
            frases.append(f"{I.lista_texto(vazios).capitalize()} não {'foi preenchido' if len(vazios) == 1 else 'foram preenchidos'} nos registros: essas análises ficam para quando houver registro.")
    if ind.get("observacoes"):
        frases.append(f"Observação: {ind['observacoes']}")
    return bloco("texto", span, titulo=f"Conclusão {DO_PERIODO[ind['tipo']]}", paragrafos=frases)


def lista_datas(datas):
    return I.lista_texto([f"{d:%d/%m}" for d in datas])


# ---------------------------------------------------------------- PKZ: testes
def comparacoes_pkz(ind, span=12, anual=False, titulo=None):
    if anual:
        base = [t for t in ind["testes"] if t["medicoes_periodo"] >= 2]
        sub = "Primeira e última medição do ano, em cada teste com duas ou mais medições no ano."
    elif ind["testes_periodo"]:
        base = ind["testes_periodo"]
        sub = "Cada teste medido no período, comparado com a sua medição anterior."
    else:
        base = [t for t in ind["testes"] if t["atual"] is not None or t["em_validacao"]]
        ult = ind["avaliacoes_todas"][-1] if ind["avaliacoes_todas"] else None
        titulo = titulo or "Resultados mais recentes"
        sub = (f"Nenhuma avaliação {NO_PERIODO[ind['tipo']]}. Abaixo, o último resultado de cada teste"
               + (f" (última avaliação em {ult:%d/%m/%Y})" if ult else "") + ", comparado com a medição anterior.")
    itens = []
    for t in base:
        if anual:
            ant, atu, sit, var = t["primeiro_periodo"], t["ultimo_periodo"], t["situacao_periodo"], t["variacao_periodo"]
            data = None
        else:
            ant, atu, sit, var = t["anterior"], t["atual"], t["situacao"], t["variacao"]
            data = t["data_ultima"]
        rotulo, cor = SITUACAO[sit]
        itens.append({"nome": t["nome"], "data": f"{data:%d/%m/%Y}" if data else None,
                      "direcao": "menor é melhor" if t["maior_melhor"] is False else "maior é melhor" if t["maior_melhor"] else "sem direção",
                      "anterior": I.com_unidade(ant, t["unidade"]) if ant is not None else "—",
                      "atual": I.com_unidade(atu, t["unidade"]) if atu is not None else I.SEM_REGISTRO,
                      "variacao": I.pct(var, sinal=True) if var is not None else None,
                      "situacao": rotulo, "cor": cor, "proporcao": _proporcao(ant, atu)})
    if not itens:
        return sem_dados(titulo or "Resultados dos testes", "Nenhum teste físico registrado até o fim do período.", span)
    return bloco("comparacoes", span, titulo=titulo or ("Primeira e última avaliação do ano" if anual else "Resultados dos testes: antes e agora"),
                 sub=sub, itens=itens, colunas_duplas=len(itens) > 4,
                 onde_resto="veja a tabela Histórico das avaliações do ano" if anual else "veja o histórico completo no relatório anual")


def _proporcao(anterior, atual):
    if anterior is None or atual is None:
        return None
    maior = max(abs(anterior), abs(atual)) or 1
    return {"anterior": abs(anterior) / maior * 100, "atual": abs(atual) / maior * 100}


def mini_evolucao(ind, span=12, colunas=4, so_ano=False):
    itens = []
    for t in ind["testes"]:
        pontos = [(d, v) for d, v in t["historico"] if not so_ano or d >= ind["inicio"]]
        if len(pontos) < 2:
            continue
        rot = [(f"{d:%d/%m/%y}", v) for d, v in pontos[-6:]]
        unidade = t["unidade"]
        itens.append({"titulo": t["nome"], "sub": ("menor é melhor" if t["maior_melhor"] is False else "maior é melhor") + (f" · {unidade}" if unidade else ""),
                      "desenhar": (lambda pts, u: lambda w, h: G.linha(pts, w, h, casas=2 if u == "s" else 1))(rot, unidade)})
    nota = None
    return bloco("mini", span, titulo="Evolução em cada teste" + (" no ano" if so_ano else ""), colunas=colunas,
                 sub=("Medições " + (f"de {ind['inicio'].year}" if so_ano else f"até {ind['fim']:%d/%m/%Y}") + ", em ordem de data (até 6 por teste)."),
                 itens=itens, nota=nota, sem_dados="Nenhum teste tem duas ou mais medições até o fim do período: a evolução aparece a partir da segunda avaliação de cada teste.")


def variacoes(ind, span=6, anual=False):
    campo_v, campo_s = ("variacao_periodo", "situacao_periodo") if anual else ("variacao", "situacao")
    base = ind["base_situacao"]
    itens = [{"rotulo": t["nome"], "valor": t[campo_v], "texto": I.pct(t[campo_v], sinal=True), "cor": SITUACAO[t[campo_s]][1]}
             for t in base if t[campo_v] is not None]
    return grafico("Variação de cada teste" + (" no ano" if anual else ""),
                   lambda w, h: G.barras_h(itens, w, h, divergente=True), span,
                   sub=("Da primeira para a última medição do ano." if anual else "Em relação à medição anterior.") + " Verde melhorou, vermelho piorou, cinza estável; laranja: regra do teste em validação, sem classificar.",
                   nota="Em testes de tempo o valor cai quando melhora: a cor já leva isso em conta.", **_barras_h(len(itens), 30),
                   sem_dados="Nenhum teste com duas medições para calcular a variação: ela aparece a partir da segunda avaliação de cada teste.")


def posicao_grupo(ind, span=6):
    itens = [{"rotulo": t["nome"], "valor": t["grupo"]["percentil"], "texto": f"{t['grupo']['percentil']}",
              "cor": "#157a4b" if t["grupo"]["percentil"] >= 67 else "#b45309" if t["grupo"]["percentil"] < 34 else "#12228E"}
             for t in ind["testes"] if t["grupo"]]
    colegas = max((t["grupo"]["colegas"] for t in ind["testes"] if t["grupo"]), default=0)
    return grafico("Posição entre os colegas", lambda w, h: G.barras_h(itens, w, h, maximo=100, marca=50), span,
                   sub=f"Percentil no último resultado, entre {colegas} colegas ({ind.get('grupo_descricao') or 'mesma faixa de idade'}). O risco marca o meio do grupo (50).",
                   sem_dados=f"Menos de {I.MINIMO_GRUPO} colegas da mesma faixa de idade com os mesmos testes: a comparação com o grupo não é feita.")


def situacao_testes(ind, span=6):
    c = ind["contagem_situacao"]
    partes = [(SITUACAO[k][0], c[k], SITUACAO[k][1]) for k in ("melhorou", "estavel", "piorou", "em_validacao", "sem_classificacao", "sem_comparacao") if c[k]]
    return grafico("Situação dos testes", lambda w, h: G.rosca(partes, w, h, centro=str(sum(c.values())), centro_sub="testes"), span, **ROSCA,
                   sub="Quantos testes melhoraram, ficaram estáveis ou pioraram " + ("da primeira para a última medição do ano." if ind["tipo"] == "anual" else "contra a medição anterior."),
                   sem_dados="Nenhum teste medido no período: não há situação para mostrar.")


def diferenca_lados(ind, span=6):
    itens = [{"rotulo": l["nome"], "valor": l["diferenca"], "texto": I.pct(l["diferenca"]),
              "cor": "#be123c" if l["diferenca"] >= 10 else "#12228E"} for l in ind["lados"]]
    return grafico("Equilíbrio entre os lados", lambda w, h: G.barras_h(itens, w, h, maximo=max([20] + [i["valor"] for i in itens])), span,
                   sub="Diferença entre direita e esquerda na última medição dos testes feitos dos dois lados. Acima de 10% fica em vermelho.",
                   sem_dados="Nenhum teste com direita e esquerda medidos na mesma avaliação.")


def reavaliacao(ind, span=6):
    r = ind.get("reavaliacao")
    if not r:
        return sem_dados("Reavaliação", "Sem data de reavaliação calculada para este atleta.", span)
    vence = ler_data(r["vence_em"])
    dias = (vence - ind["fim"]).days  # situação no fim do período do relatório, não no dia em que ele é gerado
    sit = "Vencida" if dias < 0 else "Vence em breve" if dias <= 30 else "Em dia"
    ultima = ler_data(r.get("ultima_avaliacao_em"))
    return bloco("kpis", span, titulo="Reavaliação", itens=[
        {"valor": sit, "rotulo": "No fim do período", "nota": "regra provisória: 90 dias", "cor": "vermelho" if dias < 0 else "primaria"},
        {"valor": f"{vence:%d/%m/%Y}", "rotulo": "Data-limite", "nota": f"última avaliação {ultima:%d/%m/%Y}" if ultima else "", "cor": "texto"}])


def avaliacoes_registradas(ind, span=6):
    datas = ind["avaliacoes_todas"]
    if not datas:
        return sem_dados("Avaliações registradas", "Nenhuma avaliação física registrada até o fim do período.", span)
    linhas = []
    for d in reversed(datas):
        testes = [t for t in ind["testes"] if any(x == d for x, _ in t["historico"])]
        validadas = sum(1 for t in testes if not t["em_validacao"])
        linhas.append([f"{d:%d/%m/%Y}", str(len(testes)), str(validadas), str(len(testes) - validadas)])
    return bloco("tabela", span, titulo="Avaliações registradas", sub="Todas as avaliações físicas até o fim do período, da mais recente para a mais antiga.",
                 colunas=["Data", "Testes", "Regra validada", "Em validação"], linhas=linhas)


def historico_eventos(ind, span=12):
    """Linha do tempo do período: sessões, avaliações e relatórios de treino, em ordem."""
    eventos = []
    for s in ind["sessoes_lista"]:
        d = ler_data(s["data"])
        eventos.append((d, s.get("hora_inicio") or "", ["", f"{I.DIAS_CURTOS[d.weekday()]} {d:%d/%m}", (s.get("hora_inicio") or "")[:5] or "—",
                                                        "Sessão", {"texto": ROTULO_STATUS[s["status"]], "cor": COR[s["status"]]}]))
    for d in ind["avaliacoes_periodo"]:
        n = sum(1 for t in ind["testes"] if any(x == d for x, _ in t["historico"]) or (t["em_validacao"] and t["data_ultima"] == d))
        eventos.append((d, "", ["", f"{I.DIAS_CURTOS[d.weekday()]} {d:%d/%m}", "—", "Avaliação física", f"{I.plural(n, 'teste', 'testes')}"]))
    for t in ind["treinos_lista"]:
        d = ler_data(t["data"])
        detalhe = " · ".join(x for x in (t.get("intensidade"), t.get("desempenho")) if x) or "sem detalhes registrados"
        eventos.append((d, "z", ["", f"{I.DIAS_CURTOS[d.weekday()]} {d:%d/%m}", "—", "Relatório de treino", detalhe]))
    eventos.sort(key=lambda e: (e[0], e[1]))
    linhas = [e[2][1:] for e in eventos]
    if not linhas:
        return sem_dados("Histórico do período", f"Nenhum registro {NO_PERIODO[ind['tipo']]}.", span)
    return bloco("tabela", span, titulo="Histórico do período", sub="Tudo o que foi registrado no período, em ordem de data.",
                 colunas=["Data", "Hora", "Registro", "Situação / detalhe"], linhas=linhas)


# ---------------------------------------------------------------- One to One: treinos
def distribuicao_oto(ind, campo, titulo, span=6, forma="rosca"):
    d = ind["dist"][campo]
    if not ind["treinos"]:
        return sem_dados(titulo, f"Nenhum relatório de treino {NO_PERIODO[ind['tipo']]}.", span)
    if not d["preenchidos"]:
        return sem_dados(titulo, f"Sem registro: o campo não foi preenchido em nenhum dos {ind['treinos']} relatórios de treino do período.", span)
    cores = ["#12228E", "#4f6bd8", "#9db2d8", "#0e1a6b", "#64748b", "#c9d3ef"]
    nota = f"{d['vazios']} relatório(s) sem este campo preenchido." if d["vazios"] else None
    if forma == "rosca":
        partes = [(nome, n, cores[i % len(cores)]) for i, (nome, n, _) in enumerate(d["itens"])]
        return grafico(titulo, lambda w, h: G.rosca(partes, w, h, centro=str(d["preenchidos"]), centro_sub="treinos"), span, **ROSCA,
                       sub="Como o professor registrou os treinos do período.", nota=nota)
    itens = [{"rotulo": nome, "valor": n, "texto": f"{n} ({I.pct(p, 0)})", "cor": cores[i % len(cores)]} for i, (nome, n, p) in enumerate(d["itens"])]
    return grafico(titulo, lambda w, h: G.barras_h(itens, w, h), span, sub="Quantidade de treinos em cada registro do professor.", nota=nota,
                   **_barras_h(len(itens)))


def treinos_tabela(ind, span=12, titulo="Treinos registrados"):
    if not ind["treinos_lista"]:
        return sem_dados(titulo, f"Nenhum relatório de treino {NO_PERIODO[ind['tipo']]}.", span)
    campos = [("tipo_treino", "Tipo"), ("objetivos", "Objetivos"), ("intensidade", "Intensidade"), ("desempenho", "Desempenho")]
    # Coluna sem nenhum registro no período não aparece.
    campos = [(c, n) for c, n in campos if any(t.get(c) for t in ind["treinos_lista"])]
    linhas = []
    for t in sorted(ind["treinos_lista"], key=lambda t: t["data"], reverse=ind["tipo"] == "anual"):
        d = ler_data(t["data"])
        linhas.append([f"{I.DIAS_CURTOS[d.weekday()]} {d:%d/%m/%Y}"] + [t.get(c) or I.SEM_REGISTRO for c, _ in campos])
    return bloco("tabela", span, titulo=titulo, sub="Cada treino como o professor registrou." + (" Campo vazio num treino aparece como sem registro." if any(
                     not t.get(c) for t in ind["treinos_lista"] for c, _ in campos) else ""),
                 colunas=["Data"] + [n for _, n in campos], linhas=linhas, onde_resto="mais antigos")


def cobertura_oto(ind, span=6):
    s = ind["sessoes"]
    sem_relatorio = max(s["presentes"] - ind["treinos"], 0)
    itens = [{"rotulo": "Presenças", "valor": s["presentes"], "texto": str(s["presentes"]), "cor": "#157a4b"},
             {"rotulo": "Treinos registrados", "valor": ind["treinos"], "texto": str(ind["treinos"]), "cor": "#12228E"},
             {"rotulo": "Presenças sem relatório", "valor": sem_relatorio, "texto": str(sem_relatorio), "cor": "#94a3b8"}]
    return grafico("Presenças e relatórios de treino", lambda w, h: G.barras_h(itens, w, h) if s["presentes"] or ind["treinos"] else None, span,
                   sub="Quantas presenças têm um relatório de treino registrado pelo professor.",
                   sem_dados=f"Sem presença nem relatório de treino {NO_PERIODO[ind['tipo']]}.")


def observacoes_oto(ind, span=12):
    obs = ind["observacoes_treino"]
    if not obs:
        return sem_dados("Observações do professor", f"Nenhuma observação escrita nos relatórios de treino {NO_PERIODO[ind['tipo']]}.", span)
    itens = [(f"{d:%d/%m/%Y}", texto) for d, texto in sorted(obs, reverse=True)]
    return bloco("lista", span, titulo="Observações do professor", tom="neutro", itens=itens, vazio="")


# ---------------------------------------------------------------- planos de página
def paginas(ind):
    tipo, pkz = ind["tipo"], ind["modalidade"] == "PKZ"
    return {"semanal": _semanal, "mensal": _mensal, "anual": _anual}[tipo](ind, pkz)


def _pagina(titulo, linhas):
    return {"titulo": titulo, "linhas": [{"altura": a, "blocos": b} for a, b in linhas]}


def _semanal(ind, pkz):
    s = ind["sessoes"]
    por_dia = grafico("Sessões em cada dia da semana", lambda w, h: G.barras(colunas_status(ind["por_dia"], sub=lambda x: f"{x['data']:%d/%m}"), w, h),
                      sub="Situação de cada sessão agendada, dia a dia.", legenda=LEGENDA_STATUS,
                      sem_dados="Nenhuma sessão agendada nesta semana.")
    p1 = _pagina("Resumo geral da semana", [
        (330, [cartao_atleta(ind), resumo(ind)]), (104, [kpis(ind)]),
        (1.0, [ao_lado_do_resumo(ind, pkz) | {"span": 5}, por_dia | {"span": 7}]),
        (0.75, [reavaliacao(ind) if pkz else cobertura_oto(ind), comparacao_periodo_anterior(ind)]),
    ])
    if pkz:
        p2 = _pagina("Desempenho nos testes físicos", [
            (1.35, [comparacoes_pkz(ind)]),
            (1.0, [variacoes(ind), posicao_grupo(ind)]),
            (1.15, [mini_evolucao(ind)]),
        ])
    else:
        p2 = _pagina("Treinos e atividades da semana", [
            (1.3, [treinos_tabela(ind, titulo="Treinos da semana")]),
            (1.0, [distribuicao_oto(ind, "intensidade", "Intensidade dos treinos"), distribuicao_oto(ind, "desempenho", "Desempenho registrado", forma="barras")]),
            (0.6, [distribuicao_oto(ind, "tipo_treino", "Tipos de treino", forma="barras"), distribuicao_oto(ind, "objetivos", "Objetivos trabalhados", forma="barras")]),
        ])
    agenda = historico_eventos(ind, 12)
    agenda["titulo"] = "Agenda completa da semana"
    if pkz:
        par = [diferenca_lados(ind), situacao_testes(ind, 6) if ind["sessoes_lista"] else avaliacoes_registradas(ind)]
    else:
        par = [observacoes_oto(ind)]
    p3 = _pagina("Análise complementar e conclusão", [
        (1.0, [agenda]),
        (1.15, par),
        (1.0, listas_destaque(ind)),
        (0.7, [conclusao(ind)]),
        (0.85, [criterios(ind)]),
    ])
    return [p1, p2, p3]


def _mensal(ind, pkz):
    semanas = ind["por_semana"]
    freq_semana = grafico("Frequência semana a semana",
                          lambda w, h: G.linha([(x["rotulo"] + " sem", x["frequencia"]) for x in semanas], w, h, unidade="%", y_de_zero=True, maximo=100, casas=0),
                          sub="Presenças ÷ (presenças + faltas) em cada semana do mês. Semana sem chamada fica sem ponto.",
                          sem_dados="Menos de duas semanas com chamada registrada: não há evolução da frequência para mostrar.")
    destaque = (situacao_testes(ind) if pkz else cobertura_oto(ind))  # a intensidade já está na página 2
    p1 = _pagina("Panorama geral do mês", [
        (330, [cartao_atleta(ind), resumo(ind)]), (104, [kpis(ind)]),
        (1.0, [ao_lado_do_resumo(ind, pkz) | {"span": 5}, destaque | {"span": 7}]),
        (0.8, [comparacao_periodo_anterior(ind, 12)]),
    ])
    if pkz:
        p2 = _pagina("Evolução e desempenho", [
            (1.35, [comparacoes_pkz(ind)]),
            (1.25, [mini_evolucao(ind)]),
            (1.0, [variacoes(ind), posicao_grupo(ind)]),
        ])
    else:
        treinos_sem = grafico("Treinos registrados por semana",
                              lambda w, h: G.barras([{"rotulo": x["rotulo"], "sub": f"{x['inicio']:%d}–{x['fim']:%d/%m}", "partes": [(x["treinos"], "#12228E")]} for x in semanas], w, h),
                              sub="Relatórios de treino finalizados pelo professor em cada semana.", sem_dados="Nenhum relatório de treino no mês.")
        p2 = _pagina("Evolução e atividades", [
            (1.0, [freq_semana]),
            (1.0, [distribuicao_oto(ind, "intensidade", "Intensidade dos treinos"), distribuicao_oto(ind, "desempenho", "Desempenho registrado", forma="barras")]),
            (0.95, [treinos_sem]),
            (0.6, [distribuicao_oto(ind, "tipo_treino", "Tipos de treino", forma="barras"), distribuicao_oto(ind, "objetivos", "Objetivos trabalhados", forma="barras")]),
        ])
    tabela_semanas = bloco("tabela", 5, titulo="Comparação entre semanas", sub="Chamada de cada semana do mês.",
                           colunas=["Semana", "Pres.", "Faltas", "Canc.", "Freq."],
                           linhas=[[f"{x['rotulo']} ({x['inicio']:%d}–{x['fim']:%d/%m})", str(x["presentes"]), str(x["faltas"]), str(x["cancelados"]),
                                    I.pct(x["frequencia"], 0) if x["frequencia"] is not None else "—"] for x in semanas])
    barras_semana = grafico("Presença semana a semana", lambda w, h: G.barras(colunas_status(semanas, sub=lambda x: f"{x['inicio']:%d}–{x['fim']:%d/%m}"), w, h), 7,
                            sub="Sessões de cada semana, por situação.", legenda=LEGENDA_STATUS, sem_dados="Nenhuma sessão agendada no mês.")
    cores_cal = {k: v for k, v in COR.items()} | {"agendado": "#dbe4ff", "cancelado": "#e2e8f0"}
    calendario = grafico(f"Calendário de {I.MESES[ind['inicio'].month - 1]}",
                         lambda w, h: G.calendario(ind["inicio"].year, ind["inicio"].month, ind["por_dia_mes"], cores_cal, w, h) if ind["por_dia_mes"] else None, 6,
                         sub="Cada dia com sessão, pela situação registrada.", legenda=[(COR["presente"], "presença"), (COR["falta"], "falta"), ("#e2e8f0", "cancelada"), ("#dbe4ff", "agendada")],
                         sem_dados="Nenhuma sessão agendada no mês.")
    dias = grafico("Presença por dia da semana", lambda w, h: G.barras(colunas_status(ind["por_dia_semana"]), w, h), 6,
                   sub="Em que dias as sessões aconteceram e como foi a chamada.", legenda=LEGENDA_STATUS, sem_dados="Nenhuma sessão agendada no mês.")
    p3 = _pagina("Análise detalhada do período", [
        (1.0, [barras_semana, tabela_semanas]),
        (1.05, [calendario, dias]),
        (1.25, [historico_eventos(ind) if pkz else treinos_tabela(ind, titulo="Histórico de treinos do mês")]),
    ])
    p4 = _pagina("Resultados e conclusão do mês", [
        (1.0, listas_destaque(ind)),
        *([] if pkz else [(0.95, [comparacao_periodo_anterior(ind)])]),
        (0.75, [conclusao(ind)]),
        (0.8, [criterios(ind)]),
    ])
    return [p1, p2, p3, p4]


def _anual(ind, pkz):
    meses = [m for m in ind["por_mes"]]
    com = ind["meses_com_dados"]
    recorte = meses[meses.index(com[0]):meses.index(com[-1]) + 1] if com else []
    freq_mes = grafico("Frequência mês a mês",
                       lambda w, h: G.linha([(m["rotulo"], m["frequencia"]) for m in recorte], w, h, unidade="%", y_de_zero=True, maximo=100, casas=0),
                       sub="Presenças ÷ (presenças + faltas) em cada mês com registro. Mês sem chamada fica sem ponto.",
                       sem_dados="Menos de dois meses com chamada registrada: não há evolução mensal da frequência para mostrar.")
    p1 = _pagina("Visão geral do ano", [
        (330, [cartao_atleta(ind), resumo(ind)]), (104, [kpis(ind)]),
        (1.0, [ao_lado_do_resumo(ind, pkz) | {"span": 5}, freq_mes | {"span": 7}]),
    ])
    if pkz:
        p2 = _pagina("Evolução ao longo do ano", [
            (1.35, [comparacoes_pkz(ind, anual=True)]),
            (1.2, [mini_evolucao(ind, so_ano=True)]),
            (1.0, [variacoes(ind, anual=True), posicao_grupo(ind)]),
        ])
    else:
        cores_int = ["#12228E", "#4f6bd8", "#9db2d8", "#0e1a6b", "#64748b"]
        nomes_int = [n for n, _, _ in ind["dist"]["intensidade"]["itens"]]
        intens_mes = grafico("Intensidade mês a mês",
                             lambda w, h: G.barras([{"rotulo": m["rotulo"], "partes": [(m["intensidades"].get(n, 0), cores_int[i % 5]) for i, n in enumerate(nomes_int)]} for m in recorte], w, h) if nomes_int else None,
                             6, sub="Treinos por mês, pela intensidade registrada.", legenda=[(cores_int[i % 5], n.lower()) for i, n in enumerate(nomes_int)],
                             sem_dados="Sem intensidade registrada nos treinos do ano.")
        p2 = _pagina("Evolução ao longo do ano", [
            (1.0, [grafico("Treinos registrados por mês", lambda w, h: G.barras([{"rotulo": m["rotulo"], "partes": [(m["treinos"], "#12228E")]} for m in recorte], w, h),
                           sub="Relatórios de treino finalizados pelo professor em cada mês.", sem_dados="Nenhum relatório de treino no ano.")]),
            (1.05, [distribuicao_oto(ind, "intensidade", "Intensidade dos treinos no ano"), intens_mes]),
            (1.0, [distribuicao_oto(ind, "desempenho", "Desempenho registrado no ano", 12, "barras")]),
            (0.6, [distribuicao_oto(ind, "tipo_treino", "Tipos de treino", forma="barras"), distribuicao_oto(ind, "objetivos", "Objetivos trabalhados", forma="barras")]),
        ])
    tabela_meses = bloco("tabela", 7, titulo="Comparação mês a mês", sub="Chamada e atividade de cada mês com registro.",
                         colunas=["Mês", "Sessões", "Pres.", "Faltas", "Canc.", "Freq.", "Aval." if pkz else "Treinos"],
                         linhas=[[I.MESES[m["mes"] - 1].capitalize(), str(m["total"]), str(m["presentes"]), str(m["faltas"]), str(m["cancelados"]),
                                  I.pct(m["frequencia"], 0) if m["frequencia"] is not None else "—",
                                  str(ind["avaliacao_por_mes"].get(m["mes"], 0)) if pkz else str(m["treinos"])] for m in recorte],
                         nota="Meses sem nenhum registro no início e no fim do ano não aparecem." if recorte and len(recorte) < 12 else None)
    tri = [t for t in ind["trimestres"] if t["total"]]
    trimestres = grafico("Comparação entre trimestres",
                         lambda w, h: G.barras([{"rotulo": t["rotulo"], "sub": f"{t['presentes']}/{t['presentes'] + t['faltas']}", "partes": [(round(t["frequencia"]), "#12228E" if pkz else "#12228E")]}
                                               for t in tri if t["frequencia"] is not None], w, h, unidade="%") if sum(t["frequencia"] is not None for t in tri) >= 2 else None, 5,
                         sub="Frequência de cada trimestre com chamada (presenças/sessões com chamada embaixo).",
                         sem_dados="Menos de dois trimestres com chamada registrada: a comparação entre trimestres não é feita.")
    destaques_tempo = []
    if ind["melhor_mes"]:
        m, p = ind["melhor_mes"], ind["pior_mes"]
        destaques_tempo += [{"valor": I.MESES[m["mes"] - 1].capitalize(), "rotulo": "Maior frequência", "nota": f"{I.pct(m['frequencia'], 0)} ({m['presentes']}/{m['base']})", "cor": "verde"},
                            {"valor": I.MESES[p["mes"] - 1].capitalize(), "rotulo": "Menor frequência", "nota": f"{I.pct(p['frequencia'], 0)} ({p['presentes']}/{p['base']})", "cor": "vermelho"}]
    if ind["mais_ativo"]:
        a = ind["mais_ativo"]
        destaques_tempo.append({"valor": I.MESES[a["mes"] - 1].capitalize(), "rotulo": "Mês mais ativo",
                                "nota": f"{I.plural(a['presentes'], 'presença', 'presenças')}" + (f" · {a['treinos']} treinos" if not pkz else ""), "cor": "primaria"})
    bloco_tempo = (bloco("kpis", 6, titulo="Períodos em destaque", itens=destaques_tempo) if destaques_tempo else
                   sem_dados("Períodos em destaque", "Menos de dois meses com chamada: não há maior e menor frequência para comparar.", 6))
    tend = ind["tendencia"]
    texto_tend = (bloco("texto", 6, titulo="Tendência da frequência", paragrafos=[
        f"Do primeiro mês com chamada ({I.MESES[tend['de']['mes'] - 1]}, {I.pct(tend['de']['frequencia'], 0)}) para o último "
        f"({I.MESES[tend['para']['mes'] - 1]}, {I.pct(tend['para']['frequencia'], 0)}), a frequência {tend['texto']} "
        f"({I.pct(tend['delta'], 0, sinal=True).replace('%', ' pontos')}).",
        f"Base: {len([m for m in ind['por_mes'] if m['base']])} meses com chamada registrada."]) if tend else
        sem_dados("Tendência da frequência", "Uma tendência só é apontada com 3 ou mais meses com chamada registrada; o ano ainda não tem essa base.", 6))
    p3 = _pagina("Análise comparativa", [
        (1.2, [tabela_meses, trimestres]),
        (0.75, [bloco_tempo, texto_tend]),
        (1.0, [grafico("Presença por dia da semana", lambda w, h: G.barras(colunas_status(ind["por_dia_semana"]), w, h),
                       sub="Em que dias da semana as sessões do ano aconteceram e como foi a chamada.", legenda=LEGENDA_STATUS,
                       sem_dados="Nenhuma sessão agendada no ano.")]),
    ])
    if pkz:
        p4 = _pagina("Histórico das avaliações", [
            (1.6, [matriz_avaliacoes(ind)]),
            (1.0, [diferenca_lados(ind), grafico("Avaliações por mês",
                    lambda w, h: G.barras([{"rotulo": I.MESES_CURTOS[m - 1], "partes": [(ind["avaliacao_por_mes"].get(m, 0), "#12228E")]} for m in range(1, 13)], w, h) if ind["avaliacoes_periodo"] else None, 6,
                    sub="Quantas avaliações físicas foram feitas em cada mês do ano.", sem_dados="Nenhuma avaliação física no ano.")]),
        ])
    else:
        p4 = _pagina("Histórico de treinamento", [
            (1.35, [resumo_mensal_oto(ind, recorte)]),
            (1.25, [treinos_tabela(ind, titulo="Treinos mais recentes do ano")]),
            (0.75, [observacoes_oto(ind)]),
        ])
    inicio_fim = inicio_fim_ano(ind, recorte)
    p5 = _pagina("Balanço anual e conclusão", [
        (1.0, listas_destaque(ind)),
        (0.8, [inicio_fim]),
        (0.8, [conclusao(ind)]),
        (0.85, [criterios(ind)]),
    ])
    return [p1, p2, p3, p4, p5]


def matriz_avaliacoes(ind):
    datas = ind["avaliacoes_periodo"][-6:]
    if not datas:
        return sem_dados("Histórico das avaliações", "Nenhuma avaliação física no ano.")
    linhas = []
    for t in ind["testes"]:
        valores = dict(t["historico"])
        linha = [t["nome"]]
        tem = False
        for d in datas:
            if d in valores:
                linha.append(I.com_unidade(valores[d], t["unidade"]))
                tem = True
            elif t["em_validacao"] and t["data_ultima"] == d:
                linha.append({"texto": "em validação", "cor": "#b45309"})
                tem = True
            else:
                linha.append("—")
        if tem:
            v = t["variacao_periodo"]
            linha.append({"texto": I.pct(v, sinal=True), "cor": SITUACAO[t["situacao_periodo"]][1]} if v is not None else "—")
            linhas.append(linha)
    return bloco("tabela", 12, titulo="Histórico das avaliações do ano", altura_linha=19, compacta=True,
                 sub="Resultado de cada teste em cada avaliação do ano. “—” = teste não feito naquela avaliação; a última coluna compara a primeira e a última medição confirmadas.",
                 colunas=["Teste"] + [f"{d:%d/%m}" for d in datas] + ["Variação"], linhas=linhas,
                 nota=f"Mostrando as {len(datas)} avaliações mais recentes do ano." if len(ind["avaliacoes_periodo"]) > 6 else None)


def resumo_mensal_oto(ind, recorte):
    if not recorte:
        return sem_dados("Resumo de cada mês", "Nenhum registro no ano.")
    linhas = []
    for m in recorte:
        a, b = I.meses_do_ano(ind["inicio"].year)[m["mes"] - 1][1:]
        tr = I.no_intervalo(ind["treinos_lista"], a, b)
        dist_i, dist_d = I.distribuicao(tr, "intensidade")["itens"], I.distribuicao(tr, "desempenho")["itens"]
        linhas.append([I.MESES[m["mes"] - 1].capitalize(), str(m["presentes"]), I.pct(m["frequencia"], 0) if m["frequencia"] is not None else "—", str(len(tr)),
                       f"{dist_i[0][0]} ({dist_i[0][1]})" if dist_i else I.SEM_REGISTRO, f"{dist_d[0][0]} ({dist_d[0][1]})" if dist_d else I.SEM_REGISTRO])
    colunas = ["Mês", "Presenças", "Freq.", "Treinos", "Intensidade mais registrada", "Desempenho mais registrado"]
    # Coluna sem nenhum registro no ano não aparece.
    manter = [k for k in range(len(colunas)) if k < 4 or any(l[k] != I.SEM_REGISTRO for l in linhas)]
    colunas, linhas = [colunas[k] for k in manter], [[l[k] for k in manter] for l in linhas]
    extras = [n for n, k in (("intensidade", 4), ("desempenho", 5)) if k in manter]
    return bloco("tabela", 12, titulo="Resumo de cada mês",
                 sub="Presenças, frequência e treinos registrados" + (f" e o registro mais frequente de {I.lista_texto(extras)}." if extras else "."),
                 colunas=colunas, linhas=linhas)


def inicio_fim_ano(ind, recorte):
    com_base = [m for m in recorte if m["base"]]
    if len(com_base) < 2:
        return sem_dados("Início e fim do ano", "Menos de dois meses com chamada registrada: não dá para comparar o começo e o fim do ano.")
    a, b = com_base[0], com_base[-1]
    linhas = [["Frequência", I.pct(a["frequencia"], 0), I.pct(b["frequencia"], 0)], ["Presenças", str(a["presentes"]), str(b["presentes"])],
              ["Faltas", str(a["faltas"]), str(b["faltas"])]]
    if ind["modalidade"] == "PKZ":
        primeiras = [t for t in ind["testes"] if t["medicoes_periodo"] >= 2]
        linhas.append(["Testes com 2+ medições no ano", "—", str(len(primeiras))])
    else:
        linhas.append(["Treinos registrados", str(a["treinos"]), str(b["treinos"])])
    return bloco("tabela", 12, titulo="Início e fim do ano", sub=f"Primeiro mês com chamada ({I.MESES[a['mes'] - 1]}) contra o último ({I.MESES[b['mes'] - 1]}).",
                 colunas=["Indicador", I.MESES[a["mes"] - 1].capitalize(), I.MESES[b["mes"] - 1].capitalize()], linhas=linhas)
