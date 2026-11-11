"""Contexto (dados + indicadores) dos relatórios HTML.

Regra do projeto: nenhum valor é inventado. Tudo aqui vem das views da API
(atleta, evolucao, presenca, treino) e de fórmulas explícitas:

* frequência        = presenças / (presenças + faltas)
* variação %        = (atual - anterior) / anterior * 100 (sem % se anterior = 0)
* situação          = melhorou/piorou conforme `maior_melhor`; estável se |Δ%| < 2;
                      "Em validação" quando o resultado não está confirmado

Blocos sem dado ficam vazios (None/lista vazia) e o template os oculta.
"""
import calendar
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import graficos_svg as gs

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DIAS_CURTOS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

LARGURAS = {
    ("PKZ", "semanal"): 820, ("PKZ", "mensal"): 820, ("PKZ", "anual"): 820,
    ("ONE_TO_ONE", "semanal"): 700, ("ONE_TO_ONE", "mensal"): 820, ("ONE_TO_ONE", "anual"): 860,
}

MARCAS = {
    "PKZ": {
        "nome": "PKZ",
        "subtitulo": "Playmakerz Lab · para pais e responsáveis",
        "rodape_extra": "Juntos, desenvolvendo atletas e construindo confiança.",
        "alt_logo": "PKZ",
    },
    "ONE_TO_ONE": {
        "nome": "One to One",
        "subtitulo": "One to One Studio · acompanhamento do aluno",
        "rodape_extra": "One to One Studio · treino individualizado para jovens adultos e adultos.",
        "alt_logo": "PKZ One to One",
    },
}

TITULOS = {"semanal": "Relatório da semana", "mensal": "Relatório do mês", "anual": "Relatório do ano"}
SUBSTANTIVO = {"semanal": "semana", "mensal": "mês", "anual": "ano"}
NO_PERIODO = {"semanal": "na semana", "mensal": "no mês", "anual": "no ano"}

ESTILO_SITUACAO = {
    "melhorou": "verde",
    "piorou": "vermelho",
    "estavel": "cinza",
    "em_validacao": "ambar",
    "sem_comparacao": "cinza",
    "sem_classificacao": "cinza",
}
COR_SITUACAO = {
    "melhorou": "verde", "piorou": "vermelho", "estavel": "azul",
    "em_validacao": "cinza", "sem_comparacao": "azul", "sem_classificacao": "azul",
}
ESTILO_STATUS = {"presente": "verde", "falta": "vermelho", "cancelado": "cinza", "agendado": "azul"}
ROTULO_STATUS = {"presente": "Presente", "falta": "Falta", "cancelado": "Cancelado", "agendado": "Agendado"}


# ---------------------------------------------------------------- utilidades
def _g():
    """Importa o gerador atual (funções de negócio já existentes e testadas)."""
    from gerador_pkz import gerar_pdf
    return gerar_pdf


def normalizar_unidade(unidade):
    return "ONE_TO_ONE" if str(unidade).upper().replace(" ", "_") in ("ONE_TO_ONE", "ONETOONE") else "PKZ"


def nome_template(unidade, periodo):
    """Nome do arquivo HTML oficial para a unidade e o período."""
    if periodo not in TITULOS:
        raise ValueError("Período inválido. Use semanal, mensal ou anual.")
    prefixo = "OneToOne" if normalizar_unidade(unidade) == "ONE_TO_ONE" else "PKZ"
    return f"{prefixo}_relatorio_{periodo}.html"


def numero(valor, casas=1):
    texto = f"{valor:.{casas}f}".replace(".", ",")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto


def rotulo_periodo(periodo, inicio, fim):
    if periodo == "semanal":
        return f"{inicio:%d/%m} a {fim:%d/%m}"
    if periodo == "mensal":
        return f"{MESES[inicio.month - 1].capitalize()} de {inicio.year}"
    return str(inicio.year)


def primeiro_nome(nome):
    partes = str(nome or "").split()
    return partes[0] if partes else "O atleta"


def iniciais(nome):
    partes = [p for p in str(nome or "").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _data(valor):
    try:
        return date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError):
        return None


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


def valor_disponivel(valor):
    if valor is None:
        return False
    texto = str(valor).strip()
    if not texto:
        return False
    return "dado ficticio de demonstracao" not in _g().normalizar(texto)


def contar_status(presencas):
    g = _g()
    contagem = Counter()
    for item in presencas:
        status = g.normalizar(item.get("status")).strip()
        if status == "aguardando_confirmacao":
            status = "agendado"
        contagem[status] += 1
    presentes, faltas = contagem["presente"], contagem["falta"]
    base = presentes + faltas
    return {
        "presentes": presentes,
        "faltas": faltas,
        "cancelados": contagem["cancelado"],
        "agendados": contagem["agendado"],
        "percentual": presentes / base * 100 if base else None,
    }


def filtrar_periodo(registros, inicio, fim, campo="data"):
    saida = []
    for item in registros:
        d = _data(item.get(campo))
        if d is not None and inicio <= d <= fim:
            saida.append(item)
    return saida


def _marca(unidade):
    return MARCAS[normalizar_unidade(unidade)]


def _base(unidade, periodo, inicio, fim, atleta):
    unidade = normalizar_unidade(unidade)
    template = nome_template(unidade, periodo)
    return {
        "unidade": unidade,
        "periodo": periodo,
        "template": template,
        "largura": LARGURAS[(unidade, periodo)],
        "marca": _marca(unidade),
        "titulo": TITULOS[periodo],
        "rotulo_periodo": rotulo_periodo(periodo, inicio, fim),
        "periodo_extenso": f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}",
        "atleta": {
            "nome": atleta.get("nome") or "Não informado",
            "primeiro_nome": primeiro_nome(atleta.get("nome")),
            "iniciais": iniciais(atleta.get("nome")),
        },
    }


def baldes_presenca(periodo, inicio, fim, presencas):
    """Presenças/faltas por semana (relatório mensal) ou por mês (anual)."""
    if periodo == "semanal":
        return []
    cor_p, cor_f = gs.COR_VERDE, gs.COR_VERMELHO
    baldes = []
    if periodo == "mensal":
        cursor = inicio
        indice = 1
        while cursor <= fim:
            fim_semana = min(cursor + timedelta(days=6 - cursor.weekday()), fim)
            itens = filtrar_periodo(presencas, cursor, fim_semana)
            c = contar_status(itens)
            sub = f"{cursor:%d/%m}" if cursor == fim_semana else f"{cursor:%d} a {fim_semana:%d/%m}"
            baldes.append({"rotulo": f"{indice}ª", "sub": sub,
                           "partes": [(c["presentes"], cor_p), (c["faltas"], cor_f)]})
            cursor = fim_semana + timedelta(days=1)
            indice += 1
    else:
        for mes in range(1, 13):
            ini = date(inicio.year, mes, 1)
            fim_mes = date(inicio.year, mes, calendar.monthrange(inicio.year, mes)[1])
            c = contar_status(filtrar_periodo(presencas, ini, fim_mes))
            baldes.append({"rotulo": MESES_CURTOS[mes - 1], "sub": None,
                           "partes": [(c["presentes"], cor_p), (c["faltas"], cor_f)]})
        # só do primeiro ao último mês com presença/falta (evita meses vazios nas pontas)
        com_dado = [i for i, b in enumerate(baldes) if sum(v for v, _ in b["partes"]) > 0]
        baldes = baldes[com_dado[0]:com_dado[-1] + 1] if com_dado else []
    if not any(sum(v for v, _ in b["partes"]) > 0 for b in baldes):
        return []
    return baldes


def agenda(presencas):
    linhas = []
    for item in sorted(presencas, key=lambda i: (str(i.get("data") or ""), str(i.get("hora_inicio") or ""))):
        d = _data(item.get("data"))
        if d is None:
            continue
        status = _g().normalizar(item.get("status")).strip()
        if status == "aguardando_confirmacao":
            status = "agendado"
        hora = str(item.get("hora_inicio") or "")[:5]
        linhas.append({
            "dia": DIAS[d.weekday()],
            "data_hora": f"{d:%d/%m}" + (f" · {hora}" if hora else ""),
            "status": ROTULO_STATUS.get(status, status.capitalize() or "—"),
            "estilo": ESTILO_STATUS.get(status, "cinza"),
            "destaque": status == "presente",
        })
    return linhas


# ------------------------------------------------------------ blocos extras
def montar_extras(unidade, periodo, inicio, fim, presencas_periodo, comparacoes=(), treinos=(), em_validacao=False):
    """Blocos de apoio (gráficos) que preenchem o fim da última página, em ordem de prioridade.

    Todos vêm de dados reais do período. Quais entram no PDF é decidido na renderização,
    conforme o espaço livre que sobra na última página.
    """
    g = _g()
    extras = []
    cont = contar_status(presencas_periodo)
    por_status = [("Presenças", cont["presentes"], gs.COR_VERDE), ("Faltas", cont["faltas"], gs.COR_VERMELHO),
                  ("Cancelados", cont["cancelados"], "#94a3b8"), ("Agendados", cont["agendados"], "#9db2d8")]
    rosca = gs.rosca(por_status)
    if rosca:
        extras.append({"id": "rosca", "titulo": "Como ficaram as sessões",
                       "subtitulo": "Distribuição de todas as sessões agendadas no período, por situação.",
                       "grafico": rosca, "legenda": []})

    variacoes = [{"nome": c["nome"], "pct": float(c["variacao_pct"]),
                  "cor": {"melhorou": gs.COR_VERDE, "piorou": gs.COR_VERMELHO}.get(c["situacao"], "#9db2d8")}
                 for c in comparacoes if c.get("variacao_pct") is not None]
    if variacoes:
        extras.append({"id": "variacao", "titulo": "Variação de cada teste",
                       "subtitulo": "Mudança percentual em relação à medição anterior. Verde melhorou, vermelho piorou "
                                    "(já considerando se menor ou maior é melhor), azul estável.",
                       "grafico": gs.barras_variacao(variacoes), "legenda": []})

    if periodo == "mensal" and presencas_periodo:
        por_dia = {}
        prioridade = {"presente": 3, "falta": 2, "agendado": 1, "cancelado": 0}
        for item in presencas_periodo:
            d = _data(item.get("data"))
            st = g.normalizar(item.get("status")).strip()
            st = "agendado" if st == "aguardando_confirmacao" else st
            if d and st in prioridade and prioridade[st] >= prioridade.get(por_dia.get(d.day), -1):
                por_dia[d.day] = st
        extras.append({"id": "calendario", "titulo": f"Calendário de {MESES[inicio.month - 1]}",
                       "subtitulo": "Cada dia com sessão, colorido pela situação.",
                       "grafico": gs.calendario_mes(inicio.year, inicio.month, por_dia),
                       "legenda": [(gs.COR_VERDE, "presença"), (gs.COR_VERMELHO, "falta"),
                                   ("#cbd5e1", "cancelado"), ("#dbe4ff", "agendado")]})

    if periodo in ("mensal", "anual") and presencas_periodo:
        dias = []
        for i in range(7):
            itens = [x for x in presencas_periodo if (d := _data(x.get("data"))) and d.weekday() == i]
            c = contar_status(itens)
            dias.append({"rotulo": DIAS_CURTOS[i], "sub": None,
                         "partes": [(c["presentes"], gs.COR_VERDE), (c["faltas"], gs.COR_VERMELHO)]})
        if any(sum(v for v, _ in b["partes"]) for b in dias):
            extras.append({"id": "dias_semana", "titulo": "Presença por dia da semana",
                           "subtitulo": "Em quais dias da semana as sessões acontecem e como foi a presença.",
                           "grafico": gs.barras_empilhadas(dias, altura=170),
                           "legenda": [(gs.COR_VERDE, "presenças"), (gs.COR_VERMELHO, "faltas")]})

    if unidade == "ONE_TO_ONE" and periodo in ("mensal", "anual") and treinos:
        baldes = []
        if periodo == "mensal":
            cursor, n = inicio, 1
            while cursor <= fim:
                fim_sem = min(cursor + timedelta(days=6 - cursor.weekday()), fim)
                baldes.append({"rotulo": f"{n}ª", "sub": f"{cursor:%d/%m}" if cursor == fim_sem else f"{cursor:%d} a {fim_sem:%d/%m}",
                               "partes": [(len(filtrar_periodo(treinos, cursor, fim_sem)), "#12228E")]})
                cursor, n = fim_sem + timedelta(days=1), n + 1
        else:
            for mes in range(1, 13):
                ini = date(inicio.year, mes, 1)
                fim_mes = date(inicio.year, mes, calendar.monthrange(inicio.year, mes)[1])
                baldes.append({"rotulo": MESES_CURTOS[mes - 1], "sub": None,
                               "partes": [(len(filtrar_periodo(treinos, ini, fim_mes)), "#12228E")]})
            com = [i for i, b in enumerate(baldes) if b["partes"][0][0] > 0]
            baldes = baldes[com[0]:com[-1] + 1] if com else []
        if baldes:
            extras.append({"id": "treinos_balde",
                           "titulo": "Treinos registrados " + ("por semana" if periodo == "mensal" else "por mês"),
                           "subtitulo": "Quantidade de relatórios de treino finalizados em cada intervalo.",
                           "grafico": gs.barras_empilhadas(baldes, altura=190),
                           "legenda": [("#12228E", "treinos registrados")]})

    linhas = []
    if presencas_periodo:
        linhas.append(("Frequência", "presenças ÷ (presenças + faltas). Cancelamentos e agendamentos não entram na conta."))
    if unidade == "PKZ":
        if comparacoes:
            linhas.append(("Variação", "(resultado atual − anterior) ÷ anterior. Cada teste é comparado só com a sua medição anterior."))
        if em_validacao:
            linhas.append(("Em validação", "resultado ainda não confirmado pela equipe: não é tratado como melhora nem piora."))
    elif treinos:
        linhas.append(("Treinos registrados", "relatórios de treino finalizados pelo professor no período."))
    if linhas:
        extras.append({"id": "como_ler", "titulo": "Como ler este relatório", "subtitulo": None,
                       "grafico": None, "legenda": [], "linhas": linhas})
    return extras


# ---------------------------------------------------------------------- PKZ
def _situacao_texto(situacao):
    return _g().formatar_situacao(situacao)


def montar_contexto_pkz(atleta, evolucoes, presencas, periodo, referencia):
    """Contexto do relatório PKZ. Retorna None se não houver dados no período."""
    g = _g()
    inicio, fim = g.periodo_datas(periodo, referencia)
    atleta = dict(atleta)

    ate_fim = [r for r in evolucoes if g.data_avaliacao(r) is not None and g.data_avaliacao(r) <= fim]
    no_periodo = [r for r in ate_fim if inicio <= g.data_avaliacao(r) <= fim]
    presencas_periodo = filtrar_periodo(presencas, inicio, fim)
    if not no_periodo and not presencas_periodo:
        return None

    ids_ate_fim = {r.get("avaliacao_id") for r in ate_fim if r.get("avaliacao_id")}
    ids_periodo = {r.get("avaliacao_id") for r in no_periodo if r.get("avaliacao_id")}
    datas_ate_fim = [g.data_avaliacao(r) for r in ate_fim]
    atleta["total_avaliacoes"] = len(ids_ate_fim)
    ultima = max(datas_ate_fim) if datas_ate_fim else None

    freq = contar_status(presencas_periodo)
    ctx = _base("PKZ", periodo, inicio, fim, atleta)
    nome1 = ctx["atleta"]["primeiro_nome"]

    # -- comparações (apenas testes medidos dentro do período; anterior = medição anterior)
    comparacoes = []
    for comp in g.montar_comparacoes(ate_fim):
        registros = [r for r in ate_fim if g.chave_teste(r) == (comp["teste"] or "outro", g.lado_normalizado(comp))]
        datas = [g.data_avaliacao(r) for r in registros]
        data_atual = max(datas) if datas else None
        if data_atual is None or data_atual < inicio:
            continue
        unidade = comp.get("unidade_medida") or ""
        situacao = comp["situacao"]
        validando = situacao == "em_validacao"
        variacao = comp.get("variacao_pct")
        item = {
            "nome": g.nome_com_lado(comp),
            "situacao": situacao,
            "situacao_texto": _situacao_texto(situacao),
            "estilo": ESTILO_SITUACAO.get(situacao, "cinza"),
            "cor": COR_SITUACAO.get(situacao, "azul"),
            "anterior": g.formatar_valor(comp["valor_anterior"], unidade) if comp["valor_anterior"] is not None else "—",
            "atual": "Em validação" if validando else g.formatar_valor(comp["valor_atual"], unidade),
            "variacao": None if validando or variacao is None else g.formatar_percentual(variacao),
            "variacao_num": None if validando else variacao,
            "menor_melhor": comp.get("maior_melhor") is False,
            "barra": None,
            "data_atual": f"{data_atual:%d/%m/%Y}",
            "valor_atual_num": comp["valor_atual"],
            "unidade": unidade,
        }
        if not validando:
            cor_barra = {"melhorou": gs.COR_VERDE, "piorou": gs.COR_VERMELHO}.get(situacao, "#9db2d8")
            item["barra"] = gs.barra_antes_agora(comp["valor_anterior"], comp["valor_atual"], cor_barra)
        comparacoes.append(item)
    ctx["comparacoes"] = comparacoes
    ctx["em_validacao"] = [c["nome"] for c in comparacoes if c["situacao"] == "em_validacao"]

    confirmadas = [c for c in comparacoes if c["situacao"] != "em_validacao"]
    contagem_sit = Counter(c["situacao"] for c in confirmadas)

    # -- cartão do atleta: resultados mais recentes dos testes do período
    itens_cartao = []
    for c in comparacoes[:6]:
        validando = c["situacao"] == "em_validacao"
        itens_cartao.append({
            "rotulo": c["nome"],
            "valor": "Em validação" if validando else g.formatar_valor(c["valor_atual_num"], ""),
            "unidade": None if validando else (c["unidade"] or None),
            "pequeno": validando,
            "cor": c["cor"],
            "nota": None if validando else c["variacao"],
        })
    partes_linha = [atleta.get("categoria")]
    if atleta.get("idade") is not None:
        partes_linha.append(f"{atleta['idade']} anos")
    ctx["card"] = {
        "numero": str(atleta["total_avaliacoes"]),
        "legenda": "avaliação" if atleta["total_avaliacoes"] == 1 else "avaliações",
        "linha": " · ".join(str(p) for p in partes_linha if p),
        "rodape": f"Última avaliação: {ultima:%d/%m/%Y}" if ultima else None,
        "itens": itens_cartao,
        "titulo_itens": "Resultados mais recentes" if itens_cartao else None,
    }

    # -- frase do período (gerada por regra a partir de números reais)
    base_freq = freq["presentes"] + freq["faltas"]
    frase = []
    if base_freq:
        frase = [(f"{nome1} compareceu a ", False), (f"{freq['presentes']} de {base_freq}", True),
                 (f" {'treino' if base_freq == 1 else 'treinos'} {NO_PERIODO[periodo]}", False)]
    elif freq["agendados"]:
        frase = [(f"{plural(freq['agendados'], 'treino agendado', 'treinos agendados')}", True),
                 (f" {NO_PERIODO[periodo]}, ainda sem registro de presença", False)]
    elif ids_periodo:
        frase = [(f"{nome1} fez ", False), (plural(len(ids_periodo), "avaliação", "avaliações"), True),
                 (f" {NO_PERIODO[periodo]}", False)]
    elif presencas_periodo:
        frase = [(plural(len(presencas_periodo), "agendamento", "agendamentos"), True),
                 (f" {NO_PERIODO[periodo]}, sem presença registrada", False)]
    apoio = []
    if freq["percentual"] is not None:
        apoio.append(f"Frequência de {numero(freq['percentual'])}% (presenças em relação a presenças e faltas).")
    if ids_periodo:
        apoio.append(f"{plural(len(ids_periodo), 'avaliação realizada', 'avaliações realizadas')} no período.")
    if confirmadas:
        apoio.append(
            f"Dos {plural(len(confirmadas), 'teste', 'testes')} medidos: "
            f"{contagem_sit['melhorou']} melhoraram, {contagem_sit['estavel']} ficaram estáveis "
            f"e {contagem_sit['piorou']} pioraram em relação à medição anterior."
        )
    if ctx["em_validacao"]:
        apoio.append(f"{plural(len(ctx['em_validacao']), 'resultado', 'resultados')} em validação pela PKZ.")
    ctx["hero"] = {"rotulo": f"O {SUBSTANTIVO[periodo]} em uma frase", "frase": frase, "apoio": " ".join(apoio)}

    # -- números do período
    tiles = []
    if base_freq or freq["cancelados"] or freq["agendados"]:
        notas = []
        if freq["cancelados"]:
            notas.append(plural(freq["cancelados"], "cancelamento", "cancelamentos"))
        if freq["agendados"]:
            notas.append(plural(freq["agendados"], "agendado", "agendados"))
        tiles.append({"valor": str(freq["presentes"]), "sufixo": f"/{base_freq}" if base_freq else "",
                      "rotulo": "Presenças", "nota": " · ".join(notas) or "treinos no período", "cor": "verde"})
        tiles.append({"valor": str(freq["faltas"]), "sufixo": "", "rotulo": "Faltas",
                      "nota": "no período", "cor": "vermelho" if freq["faltas"] else "azul"})
        tiles.append({"valor": f"{numero(freq['percentual'])}%" if freq["percentual"] is not None else "—",
                      "sufixo": "", "rotulo": "Frequência",
                      "nota": "presenças ÷ (presenças + faltas)", "cor": "azul"})
    if ids_periodo:
        tiles.append({"valor": str(len(ids_periodo)), "sufixo": "", "rotulo": "Avaliações",
                      "nota": f"{len(no_periodo)} resultados registrados", "cor": "azul"})
    ctx["numeros"] = tiles
    ctx["numeros_sub"] = (
        f"Consolidado de {ctx['periodo_extenso']}. O percentual considera apenas presenças e faltas."
        if tiles else None
    )
    ctx["agenda"] = agenda(presencas_periodo) if periodo == "semanal" else []

    baldes = baldes_presenca(periodo, inicio, fim, presencas_periodo)
    ctx["grafico_presenca"] = gs.barras_empilhadas(baldes, altura=155) if baldes else None
    ctx["grafico_presenca_legenda"] = [(gs.COR_VERDE, "presenças"), (gs.COR_VERMELHO, "faltas")]
    ctx["grafico_presenca_titulo"] = "Presença semana a semana" if periodo == "mensal" else "Presença mês a mês"

    # -- evolução por teste (somente valores confirmados)
    ctx["evolucao"] = []
    if periodo in ("mensal", "anual"):
        base_evolucao = ate_fim if periodo == "mensal" else no_periodo
        grupos = defaultdict(list)
        for r in base_evolucao:
            if r.get("confirmado") is True and r.get("valor") is not None:
                grupos[g.chave_teste(r)].append(r)
        for _chave, regs in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1] or ""))):
            regs.sort(key=lambda r: g.data_avaliacao(r))
            pontos = [(f"{g.data_avaliacao(r):%d/%m/%y}", r["valor"]) for r in regs]
            if len(pontos) < 2:
                continue
            direcao = next((r.get("maior_melhor") for r in reversed(regs) if r.get("maior_melhor") is not None), None)
            ctx["evolucao"].append({
                "nome": g.nome_com_lado(regs[0]),
                "unidade": regs[0].get("unidade_medida") or "",
                "pontos": pontos,
                "menor_melhor": direcao is False,
            })
        # Até 3 testes, gráficos largos; a partir de 4, até 5 por linha, desenhados já no tamanho menor
        # para os números dentro do gráfico continuarem legíveis.
        largura, altura = (360, 104) if len(ctx["evolucao"]) <= 3 else (210, 92)
        for e in ctx["evolucao"]:
            e["grafico"] = gs.linha_evolucao(e.pop("pontos"), largura=largura, altura=altura)
    ctx["evolucao_sub"] = (
        f"Resultados confirmados até {fim:%d/%m/%Y}" if periodo == "mensal" else f"Resultados confirmados em {inicio.year}"
    )

    # -- destaques calculados
    def descreve(c):
        txt = f"{c['anterior']} → {c['atual']}"
        return {"titulo": c["nome"], "texto": txt + (f" ({c['variacao']})" if c["variacao"] else "")}
    ctx["foi_bem"] = [descreve(c) for c in confirmadas if c["situacao"] == "melhorou"] if periodo != "semanal" else []
    ctx["atencao"] = [descreve(c) for c in confirmadas if c["situacao"] == "piorou"] if periodo != "semanal" else []

    # -- linha do tempo de avaliações (anual)
    ctx["avaliacoes"] = []
    if periodo == "anual":
        por_avaliacao = defaultdict(list)
        for r in no_periodo:
            por_avaliacao[(g.data_avaliacao(r), r.get("avaliacao_id"))].append(r)
        for (d, _aid), regs in sorted(por_avaliacao.items(), key=lambda kv: kv[0][0]):
            ctx["avaliacoes"].append({
                "data": f"{d:%d/%m/%Y}",
                "testes": len(regs),
                "validados": sum(1 for r in regs if r.get("confirmado") is True),
            })
    ctx["extras"] = montar_extras("PKZ", periodo, inicio, fim, presencas_periodo,
                                  [dict(c, variacao_pct=c["variacao_num"]) for c in confirmadas],
                                  em_validacao=bool(ctx["em_validacao"]))
    ctx["nota_validacao"] = bool(ctx["em_validacao"] or any(r.get("confirmado") is not True for r in no_periodo))
    return ctx


# ------------------------------------------------------------- One to One
def _distribuicao(itens, campo):
    g = _g()
    contagem = Counter()
    nomes = {}
    for t in itens:
        v = t.get(campo)
        if valor_disponivel(v):
            chave = g.normalizar(v).strip()
            contagem[chave] += 1
            nomes.setdefault(chave, str(v).strip())
    total = sum(contagem.values())
    if not total:
        return []
    return [{"nome": nomes[k][:1].upper() + nomes[k][1:], "quantidade": q, "percentual": q / total * 100}
            for k, q in contagem.most_common()]


def montar_contexto_one_to_one(atleta, presencas, treinos, periodo, referencia):
    """Contexto do relatório One to One. Retorna None se não houver dados no período.

    Não há nenhuma informação de dor neste relatório.
    """
    g = _g()
    inicio, fim = g.periodo_datas(periodo, referencia)
    presencas = filtrar_periodo(presencas, inicio, fim)
    treinos = filtrar_periodo(treinos, inicio, fim)
    if not presencas and not treinos:
        return None

    freq = contar_status(presencas)
    ctx = _base("ONE_TO_ONE", periodo, inicio, fim, atleta)
    nome1 = ctx["atleta"]["primeiro_nome"]
    base_freq = freq["presentes"] + freq["faltas"]

    treinos_ordenados = sorted(treinos, key=lambda t: str(t.get("data") or ""))
    exibidos = treinos_ordenados[-10:] if periodo == "anual" else treinos_ordenados
    campos = [("objetivos", "Objetivos"), ("tipo_treino", "Tipo de treino"),
              ("intensidade", "Intensidade"), ("desempenho", "Desempenho")]
    campos_exibidos = [c for c in campos if any(valor_disponivel(t.get(c[0])) for t in exibidos)]

    tipos = _distribuicao(treinos, "tipo_treino")
    intensidades = _distribuicao(treinos, "intensidade")

    partes_linha = ["One to One"]
    if atleta.get("idade") is not None:
        partes_linha.append(f"{atleta['idade']} anos")
    itens = [
        {"rotulo": "Presenças", "valor": str(freq["presentes"]), "cor": "verde", "pequeno": False, "nota": None, "unidade": None},
        {"rotulo": "Faltas", "valor": str(freq["faltas"]), "cor": "vermelho" if freq["faltas"] else "azul",
         "pequeno": False, "nota": None, "unidade": None},
        {"rotulo": "Frequência", "valor": f"{numero(freq['percentual'])}%" if freq["percentual"] is not None else "—",
         "cor": "azul", "pequeno": False, "nota": None, "unidade": None},
        {"rotulo": "Cancelados", "valor": str(freq["cancelados"]), "cor": "azul", "pequeno": False, "nota": None, "unidade": None},
        {"rotulo": "Agendados", "valor": str(freq["agendados"]), "cor": "azul", "pequeno": False, "nota": None, "unidade": None},
    ]
    ctx["card"] = {
        "numero": str(len(treinos)),
        "legenda": "treino registrado" if len(treinos) == 1 else "treinos registrados",
        "linha": " · ".join(partes_linha),
        "rodape": None,
        "itens": itens,
        "titulo_itens": None,
    }

    frase = []
    if base_freq:
        frase = [(f"{nome1} compareceu a ", False), (f"{freq['presentes']} de {base_freq}", True),
                 (f" {'sessão' if base_freq == 1 else 'sessões'} {NO_PERIODO[periodo]}", False)]
    elif treinos:
        frase = [(f"{nome1} teve ", False), (plural(len(treinos), "treino registrado", "treinos registrados"), True),
                 (f" {NO_PERIODO[periodo]}", False)]
    else:
        frase = [(f"{plural(freq['agendados'], 'sessão agendada', 'sessões agendadas')}", True),
                 (f" {NO_PERIODO[periodo]}, ainda sem registro de presença", False)]
    apoio = []
    if freq["percentual"] is not None:
        apoio.append(f"Frequência de {numero(freq['percentual'])}% (presenças em relação a presenças e faltas).")
    if treinos:
        apoio.append(f"{plural(len(treinos), 'treino registrado', 'treinos registrados')} no período.")
    if tipos:
        apoio.append(f"Tipo de treino mais frequente: {tipos[0]['nome']}.")
    if intensidades:
        apoio.append(f"Intensidade mais frequente: {intensidades[0]['nome']}.")
    ctx["hero"] = {"rotulo": f"Resumo {'da' if periodo == 'semanal' else 'do'} {SUBSTANTIVO[periodo]}",
                   "frase": frase, "apoio": " ".join(apoio)}

    tiles = []
    if presencas:
        notas = []
        if freq["cancelados"]:
            notas.append(plural(freq["cancelados"], "cancelamento", "cancelamentos"))
        if freq["agendados"]:
            notas.append(plural(freq["agendados"], "agendada", "agendadas"))
        tiles.append({"valor": str(freq["presentes"]), "sufixo": f"/{base_freq}" if base_freq else "",
                      "rotulo": "Sessões", "nota": " · ".join(notas) or "no período", "cor": "verde"})
        tiles.append({"valor": str(freq["faltas"]), "sufixo": "", "rotulo": "Faltas", "nota": "no período",
                      "cor": "vermelho" if freq["faltas"] else "azul"})
        tiles.append({"valor": f"{numero(freq['percentual'])}%" if freq["percentual"] is not None else "—",
                      "sufixo": "", "rotulo": "Frequência", "nota": "presenças ÷ (presenças + faltas)", "cor": "azul"})
    tiles.append({"valor": str(len(treinos)), "sufixo": "", "rotulo": "Treinos registrados",
                  "nota": "relatórios finalizados", "cor": "azul"})
    ctx["numeros"] = tiles
    ctx["numeros_sub"] = (f"Consolidado de {ctx['periodo_extenso']}. "
                          "O percentual considera apenas presenças e faltas; cancelamentos e agendamentos ficam de fora.")
    ctx["agenda"] = agenda(presencas) if periodo == "semanal" else []

    baldes = baldes_presenca(periodo, inicio, fim, presencas)
    ctx["grafico_presenca"] = gs.barras_empilhadas(baldes, altura=155) if baldes else None
    ctx["grafico_presenca_legenda"] = [(gs.COR_VERDE, "presenças"), (gs.COR_VERMELHO, "faltas")]
    ctx["grafico_presenca_titulo"] = "Presença semana a semana" if periodo == "mensal" else "Presença mês a mês"

    ctx["distribuicoes"] = [d for d in (("Tipo de treino", tipos), ("Intensidade", intensidades)) if d[1]] \
        if periodo != "semanal" else []

    ctx["treinos_campos"] = [c[1] for c in campos_exibidos]
    ctx["treinos"] = [{
        "data": f"{DIAS_CURTOS[d.weekday()]} {d:%d/%m/%Y}" if (d := _data(t.get("data"))) else "—",
        "campos": [str(t.get(c[0])).strip() if valor_disponivel(t.get(c[0])) else "—" for c in campos_exibidos],
    } for t in exibidos]
    ctx["treinos_total"] = len(treinos)
    ctx["treinos_limitados"] = periodo == "anual" and len(treinos) > 10
    ctx["treinos_sem_detalhe"] = bool(exibidos) and not campos_exibidos
    ctx["extras"] = montar_extras("ONE_TO_ONE", periodo, inicio, fim, presencas, treinos=treinos)
    return ctx
