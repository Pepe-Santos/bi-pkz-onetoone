"""Indicadores dos relatórios v2, calculados só a partir do contrato validado.

Regras (as mesmas do projeto, agora num lugar só):
* frequência   = presenças ÷ (presenças + faltas) × 100. Cancelada não é falta; agendada não é presença.
                 Sem presença nem falta no recorte, a frequência é "sem registro" (nunca 0%).
* variação %   = (atual − anterior) ÷ anterior × 100; sem % quando o anterior é 0.
* situação     = melhorou/piorou conforme maior_melhor (num teste de tempo, cair é melhorar);
                 estável se |variação| < 2%; "sem classificação" se o teste não tem direção definida.
* regra em validação = confirmado falso na API: a PKZ ainda não validou a regra do teste (direção,
                 unidade). Pelo contrato (backend/docs/api.md), o resultado aparece com os valores e a
                 variação, mas sem dizer se melhorou ou piorou, e fica fora da posição no grupo.
* tendência    = só com 3 ou mais meses com presença ou falta; compara o primeiro e o último deles.
* posição no grupo = percentil entre colegas da mesma faixa de idade, só com 5 ou mais colegas
                 com o mesmo teste confirmado.

Valores ausentes ficam None e cada tela diz por quê: SEM_REGISTRO, EM_VALIDACAO ou NAO_APLICAVEL.
"""
import calendar
from collections import Counter, defaultdict
from datetime import date, timedelta

from .contrato import ler_data

SEM_REGISTRO, EM_VALIDACAO, NAO_APLICAVEL = "Sem registro", "Em validação", "Não se aplica"
ESTAVEL_PCT = 2
MINIMO_GRUPO = 5
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DIAS_CURTOS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
LADOS = {"dir": "direita", "esq": "esquerda"}


# ---------------------------------------------------------------- formatação
def num(valor, casas=1):
    if valor is None:
        return None
    texto = f"{valor:.{casas}f}".replace(".", ",")
    return texto.rstrip("0").rstrip(",") if "," in texto else texto


def pct(valor, casas=1, sinal=False):
    if valor is None:
        return None
    texto = num(abs(valor) if sinal else valor, casas) + "%"
    if sinal:
        return ("+" if valor > 0 else "−" if valor < 0 else "") + texto
    return texto


def com_unidade(valor, unidade):
    if valor is None:
        return None
    casas = 2 if unidade == "s" else 1
    texto = num(valor, casas)
    return f"{texto} {unidade}".strip() if unidade else texto


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def lista_texto(itens):
    itens = [i for i in itens if i]
    if not itens:
        return ""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


# ---------------------------------------------------------------- sessões
def contar(sessoes, hoje):
    c = Counter(s["status"] for s in sessoes)
    pendentes = sum(1 for s in sessoes if s["status"] == "agendado" and ler_data(s["data"]) < hoje)
    base = c["presente"] + c["falta"]
    return {"total": len(sessoes), "presentes": c["presente"], "faltas": c["falta"], "cancelados": c["cancelado"],
            "agendados": c["agendado"], "pendentes": pendentes, "futuras": c["agendado"] - pendentes, "base": base,
            "frequencia": c["presente"] / base * 100 if base else None}


def no_intervalo(registros, inicio, fim, campo="data"):
    return [r for r in registros if inicio <= ler_data(r[campo]) <= fim]


def semanas_do_mes(inicio, fim):
    """Semanas (segunda a domingo) recortadas ao mês: [(rótulo, início, fim)]."""
    saida, cursor, n = [], inicio, 1
    while cursor <= fim:
        fim_semana = min(cursor + timedelta(days=6 - cursor.weekday()), fim)
        saida.append((f"{n}ª", cursor, fim_semana))
        cursor, n = fim_semana + timedelta(days=1), n + 1
    return saida


def meses_do_ano(ano):
    return [(MESES_CURTOS[m - 1], date(ano, m, 1), date(ano, m, calendar.monthrange(ano, m)[1])) for m in range(1, 13)]


def periodo_anterior(tipo, inicio):
    if tipo == "semanal":
        return inicio - timedelta(days=7), inicio - timedelta(days=1)
    if tipo == "mensal":
        fim = inicio - timedelta(days=1)
        return fim.replace(day=1), fim
    return date(inicio.year - 1, 1, 1), date(inicio.year - 1, 12, 31)


# ---------------------------------------------------------------- testes físicos (PKZ)
def nome_teste(r):
    lado = LADOS.get(r.get("lado"))
    return f"{r['teste_nome']} ({lado})" if lado else r["teste_nome"]


def situacao(anterior, atual, maior_melhor):
    if anterior is None or atual is None:
        return "sem_comparacao", None
    variacao = (atual - anterior) / abs(anterior) * 100 if anterior else None
    if abs(anterior) < 5 and float(anterior).is_integer() and float(atual).is_integer():
        variacao = None  # contagem pequena (ex.: de 1 para 0): o percentual engana; vale o "de X para Y"
    if maior_melhor is None:
        return "sem_classificacao", variacao
    if atual == anterior or (variacao is not None and abs(variacao) < ESTAVEL_PCT):  # contagem pequena: só igual é estável
        return "estavel", variacao
    melhorou = (atual > anterior) == bool(maior_melhor)
    return ("melhorou" if melhorou else "piorou"), variacao


def percentil(valor, grupo, maior_melhor):
    abaixo = sum((v < valor) if maior_melhor else (v > valor) for v in grupo)
    iguais = sum(v == valor for v in grupo)
    return round(100 * (abaixo + 0.5 * iguais) / len(grupo))


def testes(avaliacoes, inicio, fim, grupo, tipo):
    """Um item por teste (e lado) com histórico até o fim do período, o atual, o anterior e o grupo."""
    por_teste = defaultdict(list)
    for r in avaliacoes:
        if ler_data(r["data_avaliacao"]) <= fim:
            por_teste[(r["teste"], r["lado"])].append(r)
    ultimos_grupo = {}
    for r in sorted(grupo, key=lambda r: r["data_avaliacao"]):
        if r["confirmado"] and ler_data(r["data_avaliacao"]) <= fim:
            ultimos_grupo[(r["aluno"], r["teste"], r["lado"])] = r["valor"]
    itens = []
    for (teste, lado), regs in por_teste.items():
        regs.sort(key=lambda r: r["data_avaliacao"])
        confirmados = [r for r in regs if r["valor"] is not None]  # todos os valores medidos, com regra validada ou não
        no_periodo = [r for r in regs if ler_data(r["data_avaliacao"]) >= inicio]
        ultimo = regs[-1]
        validando = not ultimo["confirmado"]  # regra do teste ainda não validada pela PKZ
        maior_melhor = next((r["maior_melhor"] for r in reversed(regs) if r["maior_melhor"] is not None), None)
        atual = confirmados[-1] if confirmados else None
        anterior = confirmados[-2] if len(confirmados) >= 2 else None
        sit, var = situacao(anterior["valor"] if anterior else None, atual["valor"] if atual else None, maior_melhor)
        if validando and sit != "sem_comparacao":
            sit = "em_validacao"  # mostra a variação, sem classificar
        conf_periodo = [r for r in no_periodo if r["valor"] is not None]  # medições do período (regra validada ou não)
        # anual: primeira e última medição confirmadas do ano
        sit_ano, var_ano = situacao(conf_periodo[0]["valor"] if len(conf_periodo) >= 2 else None,
                                    conf_periodo[-1]["valor"] if len(conf_periodo) >= 2 else None, maior_melhor)
        if validando and sit_ano != "sem_comparacao":
            sit_ano = "em_validacao"
        grupo_vals = [v for (aluno, t, l), v in ultimos_grupo.items() if t == teste and l == lado]
        pos = None
        if atual and not validando and maior_melhor is not None and len(grupo_vals) >= MINIMO_GRUPO:
            pos = {"percentil": percentil(atual["valor"], grupo_vals + [atual["valor"]], maior_melhor),
                   "colegas": len(grupo_vals), "media": sum(grupo_vals) / len(grupo_vals)}
        itens.append({
            "teste": teste, "lado": lado, "nome": nome_teste(ultimo), "unidade": ultimo["unidade_medida"],
            "maior_melhor": maior_melhor, "historico": [(ler_data(r["data_avaliacao"]), r["valor"]) for r in confirmados],
            "medido_no_periodo": bool(no_periodo), "em_validacao": validando,
            "valor_em_validacao": None,
            "data_ultima": ler_data(ultimo["data_avaliacao"]),
            "atual": atual["valor"] if atual else None, "data_atual": ler_data(atual["data_avaliacao"]) if atual else None,
            "anterior": anterior["valor"] if anterior else None,
            "data_anterior": ler_data(anterior["data_avaliacao"]) if anterior else None,
            "situacao": sit, "variacao": var,
            "situacao_periodo": sit_ano, "variacao_periodo": var_ano,
            "primeiro_periodo": conf_periodo[0]["valor"] if conf_periodo else None,
            "ultimo_periodo": conf_periodo[-1]["valor"] if conf_periodo else None,
            "medicoes_periodo": len(conf_periodo), "grupo": pos,
        })
    itens.sort(key=lambda i: (i["nome"]))
    return itens


def diferencas_entre_lados(lista):
    """Para testes com direita e esquerda: diferença % entre os lados na última medição em comum."""
    por_teste = defaultdict(dict)
    for t in lista:
        if t["lado"] in ("dir", "esq") and t["historico"]:
            por_teste[t["teste"]][t["lado"]] = t
    saida = []
    for teste, lados in por_teste.items():
        if len(lados) == 2:
            d = dict(lados["dir"]["historico"])
            e = dict(lados["esq"]["historico"])
            comuns = sorted(set(d) & set(e))
            if comuns and max(d[comuns[-1]], e[comuns[-1]]):
                maior, menor = max(d[comuns[-1]], e[comuns[-1]]), min(d[comuns[-1]], e[comuns[-1]])
                saida.append({"nome": lados["dir"]["nome"].rsplit(" (", 1)[0], "data": comuns[-1],
                              "diferenca": (maior - menor) / maior * 100, "dir": d[comuns[-1]], "esq": e[comuns[-1]],
                              "unidade": lados["dir"]["unidade"]})
    return saida


# ---------------------------------------------------------------- treinos (One to One)
def distribuicao(treinos, campo):
    valores = [t[campo] for t in treinos if t.get(campo)]
    contagem = Counter(v.strip().capitalize() for v in valores)
    total = sum(contagem.values())
    return {"itens": [(k, n, n / total * 100) for k, n in contagem.most_common()], "preenchidos": total,
            "vazios": len(treinos) - total}


# ---------------------------------------------------------------- tudo
def calcular(c, hoje=None):
    hoje = hoje or date.today()
    tipo = c["tipo_relatorio"]
    inicio, fim = ler_data(c["periodo"]["inicio"]), ler_data(c["periodo"]["fim"])
    sess = no_intervalo(c["sessoes"], inicio, fim)
    trein = no_intervalo(c["treinos"], inicio, fim)
    ind = {"tipo": tipo, "modalidade": c["modalidade"], "inicio": inicio, "fim": fim, "hoje": hoje, "aluno": c["aluno"],
           "observacoes": c.get("observacoes"), "ano_incompleto": "ano_incompleto" in c.get("avisos", []),
           "origem": c.get("origem") or {}}
    ind["sessoes"] = contar(sess, hoje)
    ind["sessoes_lista"] = sess
    ind["sem_sessoes"] = not sess

    # recortes no tempo
    if tipo == "semanal":
        ind["por_dia"] = [{"rotulo": DIAS_CURTOS[i], "data": inicio + timedelta(days=i),
                           **contar([s for s in sess if ler_data(s["data"]) == inicio + timedelta(days=i)], hoje)}
                          for i in range(7)]
    ind["por_dia_semana"] = [{"rotulo": DIAS_CURTOS[i],
                              **contar([s for s in sess if ler_data(s["data"]).weekday() == i], hoje)} for i in range(7)]
    if tipo == "mensal":
        ind["por_semana"] = [{"rotulo": r, "inicio": a, "fim": b, **contar(no_intervalo(sess, a, b), hoje),
                              "treinos": len(no_intervalo(trein, a, b))} for r, a, b in semanas_do_mes(inicio, fim)]
        ind["por_dia_mes"] = {}
        prioridade = {"presente": 3, "falta": 2, "agendado": 1, "cancelado": 0}
        for s in sess:
            d = ler_data(s["data"]).day
            if prioridade[s["status"]] >= prioridade.get(ind["por_dia_mes"].get(d), -1):
                ind["por_dia_mes"][d] = s["status"]
    if tipo == "anual":
        ind["por_mes"] = [{"rotulo": r, "mes": a.month, **contar(no_intervalo(sess, a, b), hoje),
                           "treinos": len(no_intervalo(trein, a, b)),
                           "intensidades": Counter((t["intensidade"] or "").capitalize() for t in no_intervalo(trein, a, b) if t["intensidade"])}
                          for r, a, b in meses_do_ano(inicio.year)]
        ind["trimestres"] = []
        for q in range(4):
            meses = ind["por_mes"][q * 3:q * 3 + 3]
            presentes, faltas = sum(m["presentes"] for m in meses), sum(m["faltas"] for m in meses)
            ind["trimestres"].append({"rotulo": f"{q + 1}º tri", "presentes": presentes, "faltas": faltas,
                                      "total": sum(m["total"] for m in meses),
                                      "frequencia": presentes / (presentes + faltas) * 100 if presentes + faltas else None})
        com_base = [m for m in ind["por_mes"] if m["base"]]
        ind["meses_com_dados"] = [m for m in ind["por_mes"] if m["total"] or m["treinos"]]
        ind["melhor_mes"] = max(com_base, key=lambda m: (m["frequencia"], m["base"])) if len(com_base) >= 2 else None
        ind["pior_mes"] = min(com_base, key=lambda m: (m["frequencia"], -m["base"])) if len(com_base) >= 2 else None
        ind["mais_ativo"] = max(ind["meses_com_dados"], key=lambda m: m["presentes"] + m["treinos"]) if ind["meses_com_dados"] else None
        if len(com_base) >= 3:
            a, b = com_base[0], com_base[-1]
            delta = b["frequencia"] - a["frequencia"]
            ind["tendencia"] = {"de": a, "para": b, "delta": delta,
                                "texto": "subiu" if delta > 5 else "caiu" if delta < -5 else "ficou estável"}
        else:
            ind["tendencia"] = None
    datas = [ler_data(s["data"]) for s in sess] + [ler_data(t["data"]) for t in trein]
    ind["cobertura"] = (min(datas), max(datas)) if datas else None

    # período anterior (só se houver registro nele)
    a_ini, a_fim = periodo_anterior(tipo, inicio)
    sess_ant = no_intervalo(c["sessoes"], a_ini, a_fim)
    trein_ant = no_intervalo(c["treinos"], a_ini, a_fim)
    ind["anterior"] = {"inicio": a_ini, "fim": a_fim, "sessoes": contar(sess_ant, hoje), "treinos": len(trein_ant),
                       "avaliacoes": len({r["avaliacao_id"] for r in no_intervalo(c["avaliacoes"], a_ini, a_fim, "data_avaliacao")})
                       } if (sess_ant or trein_ant) else None

    # PKZ
    aval_periodo = no_intervalo(c["avaliacoes"], inicio, fim, "data_avaliacao")
    ind["avaliacoes_periodo"] = sorted({ler_data(r["data_avaliacao"]) for r in aval_periodo})
    ind["avaliacoes_todas"] = sorted({ler_data(r["data_avaliacao"]) for r in c["avaliacoes"] if ler_data(r["data_avaliacao"]) <= fim})
    ind["resultados_periodo"] = len(aval_periodo)
    ind["resultados_validacao"] = sum(1 for r in aval_periodo if not r["confirmado"])  # regra ainda não validada
    ind["testes"] = testes(c["avaliacoes"], inicio, fim, c["grupo"]["avaliacoes"], tipo) if c["modalidade"] == "PKZ" else []
    ind["testes_periodo"] = [t for t in ind["testes"] if t["medido_no_periodo"]]
    ind["lados"] = diferencas_entre_lados(ind["testes"])
    ind["grupo_descricao"] = c["grupo"].get("descricao")
    ind["reavaliacao"] = c.get("reavaliacao")
    if c["modalidade"] == "PKZ":
        base = ind["testes_periodo"] if tipo != "anual" else [t for t in ind["testes"] if t["medicoes_periodo"] >= 2]
        campo = "situacao" if tipo != "anual" else "situacao_periodo"
        ind["contagem_situacao"] = Counter(t[campo] for t in base)
        ind["base_situacao"] = base
        ind["campo_situacao"] = campo
        ind["campo_variacao"] = "variacao" if tipo != "anual" else "variacao_periodo"
        ind["avaliacao_por_mes"] = Counter(d.month for d in ind["avaliacoes_periodo"]) if tipo == "anual" else None

    # One to One
    ind["treinos_lista"] = trein
    ind["treinos"] = len(trein)
    if c["modalidade"] == "ONE_TO_ONE":
        ind["dist"] = {campo: distribuicao(trein, campo) for campo in ("tipo_treino", "intensidade", "objetivos", "desempenho")}
        ind["observacoes_treino"] = [(ler_data(t["data"]), t["observacoes"]) for t in trein if t.get("observacoes")]
        ind["cobertura_relatorio"] = (len(trein), ind["sessoes"]["presentes"])

    from . import cartao
    if c["modalidade"] == "PKZ":
        ind["cartao"] = cartao.calcular(c, fim)
        ind["evolucao_nota"] = cartao.evolucao_da_nota(c, inicio, fim)
    else:
        ind["cartao"] = cartao.calcular_one_to_one(c, inicio, fim)
    ind["destaques"] = destaques(ind)
    return ind


# ---------------------------------------------------------------- fatos para os textos (sem julgamento sem base)
def destaques(ind):
    """Pontos positivos e de atenção, cada um com o número que o sustenta."""
    s, positivos, atencao = ind["sessoes"], [], []
    if s["base"]:
        if s["faltas"] == 0:
            positivos.append(("Nenhuma falta", f"{plural(s['presentes'], 'presença', 'presenças')} e nenhuma falta registrada no período."))
        else:
            atencao.append((plural(s["faltas"], "falta registrada", "faltas registradas"),
                            f"Frequência de {pct(s['frequencia'])}: {s['presentes']} presenças em {s['base']} sessões com chamada."))
    if s["pendentes"]:
        atencao.append((plural(s["pendentes"], "sessão sem chamada", "sessões sem chamada"),
                        "Continuam como agendadas depois da data: não entram na frequência até o registro."))
    ant = ind.get("anterior")
    if ant and ant["sessoes"]["frequencia"] is not None and s["frequencia"] is not None:
        delta = s["frequencia"] - ant["sessoes"]["frequencia"]
        texto = f"{pct(ant['sessoes']['frequencia'])} → {pct(s['frequencia'])} em relação ao período anterior."
        if delta >= 5:
            positivos.append(("Frequência subiu", texto))
        elif delta <= -5:
            atencao.append(("Frequência caiu", texto))
    if ind["modalidade"] == "PKZ":
        campo_s, campo_v = ind["campo_situacao"], ind["campo_variacao"]
        for t in ind["base_situacao"]:
            v = pct(t[campo_v], sinal=True) if t[campo_v] is not None else ""
            if t[campo_s] == "melhorou":
                positivos.append((f"{t['nome']} melhorou", f"{v} ({'menor é melhor' if t['maior_melhor'] is False else 'maior é melhor'})."))
            elif t[campo_s] == "piorou":
                atencao.append((f"{t['nome']} piorou", f"{v} ({'menor é melhor' if t['maior_melhor'] is False else 'maior é melhor'})."))
        validacao = [t["nome"] for t in ind["testes_periodo"] if t["em_validacao"]]
        if validacao:
            atencao.append((plural(len(validacao), "teste com regra em validação", "testes com regra em validação"),
                            "Os resultados aparecem com os valores, mas sem dizer se melhorou ou piorou até a PKZ validar a regra."))
        for l in ind["lados"]:
            if l["diferenca"] >= 10:
                atencao.append((f"Diferença entre lados: {l['nome']}",
                                f"{pct(l['diferenca'])} entre direita ({com_unidade(l['dir'], l['unidade'])}) e esquerda "
                                f"({com_unidade(l['esq'], l['unidade'])}) em {l['data']:%d/%m/%Y}."))
        r = ind.get("reavaliacao")
        if r and r.get("situacao") == "vencida" and ler_data(r["vence_em"]) <= ind["fim"]:
            atencao.append(("Reavaliação vencida", f"A data-limite era {ler_data(r['vence_em']):%d/%m/%Y}."))
    else:
        tr, presentes = ind["cobertura_relatorio"]
        if presentes and tr >= presentes:
            positivos.append(("Treinos documentados", f"Relatório de treino em {tr} de {presentes} presenças."))
        elif presentes and tr < presentes:
            atencao.append(("Treinos sem relatório", f"{presentes - tr} de {presentes} presenças sem relatório de treino registrado."))
    return {"positivos": positivos, "atencao": atencao}
