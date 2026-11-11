# -*- coding: utf-8 -*-
"""Gera a base FICTÍCIA da cópia de teste, no mesmo formato das views da API (backend/docs/api.md).

Os mesmos alunos alimentam todas as telas: atleta.json, evolucao.json, comparacao.json, presenca.json e
treino.json. Nada aqui é dado real: nomes, idades e resultados são inventados, com semente fixa, para a
base sair igual toda vez que o script roda.

Como os números são montados, para não ficarem aleatórios sem sentido:
- cada teste tem um valor típico por idade e sexo (curvas de referência aproximadas para crianças e adultos);
- cada aluno tem um "nível" próprio, que puxa todos os testes dele para o mesmo lado, mais uma variação por teste;
- de uma avaliação para a outra, o aluno costuma melhorar um pouco, com alguns testes estáveis ou piores.

Para rodar, nesta pasta: python gerar_dados_ficticios.py AAAA-MM-DD (o dia da apresentação; sem data, usa hoje)
"""
import json
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = Path(__file__).resolve().parent / "dados_ficticios"
# Dia da apresentação: a chamada vai até ele, para o "Resumo do dia" ter sessões. Ex.: python gerar_dados_ficticios.py 2026-11-11
HOJE = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
ESTAVEL_PCT = 2  # parâmetro variacao_estavel_pct da API
sorte = random.Random(20261110)

# ---------------------------------------------------------------- nomes
MENINOS = ["Arthur", "Bernardo", "Davi", "Enzo", "Gabriel", "Heitor", "Lorenzo", "Lucas", "Matheus", "Miguel", "Pedro",
           "Rafael", "Samuel", "Theo", "Vicente", "Benício", "Caio", "Daniel", "Eduardo", "Felipe", "Gustavo", "Henrique",
           "Igor", "João Pedro", "Kauã", "Leonardo", "Murilo", "Nicolas", "Otávio", "Paulo", "Renan", "Tiago", "Vitor",
           "Bruno", "Diego", "Fábio", "Marcelo", "Rodrigo", "Thiago", "André", "Ricardo", "Fernando"]
MENINAS = ["Alice", "Helena", "Laura", "Manuela", "Valentina", "Sofia", "Isabela", "Heloísa", "Lívia", "Júlia", "Cecília",
           "Maria Clara", "Lorena", "Beatriz", "Mariana", "Giovanna", "Lara", "Clara", "Yasmin", "Antonella", "Elisa",
           "Esther", "Rebeca", "Luana", "Marina", "Nina", "Olívia", "Pietra", "Sarah", "Vitória", "Camila", "Patrícia",
           "Fernanda", "Juliana", "Renata", "Carolina", "Tatiana", "Aline", "Daniela", "Priscila", "Bianca", "Letícia"]
SOBRENOMES = ["Albuquerque", "Barcellos", "Cardoso", "Dantas", "Esteves", "Falcão", "Guimarães", "Hollanda", "Ibrahim",
              "Junqueira", "Lacerda", "Magalhães", "Nogueira", "Oliveira", "Pacheco", "Quintela", "Rezende", "Sampaio",
              "Teixeira", "Uchôa", "Vasconcellos", "Werneck", "Xavier", "Zanetti", "Brandão", "Coutinho", "Drummond",
              "Fontes", "Gusmão", "Lins", "Monteiro", "Novaes", "Pimentel", "Queiroz", "Siqueira", "Toledo", "Valadares",
              "Arantes", "Bittencourt", "Campello", "Duarte", "Figueira", "Godoy", "Leme", "Moraes", "Paranhos"]
usados: set[str] = set()


def novo_nome(sexo: str) -> str:
    while True:
        primeiro = sorte.choice(MENINOS if sexo == "M" else MENINAS)
        nome = f"{primeiro} {sorte.choice(SOBRENOMES)} {sorte.choice(SOBRENOMES)}"
        if nome not in usados and len(set(nome.split()[-2:])) == 2:
            usados.add(nome)
            return nome


def novo_id() -> str:
    return str(uuid.UUID(int=sorte.getrandbits(128), version=4))


# ---------------------------------------------------------------- testes
# teste: (nome, unidade, maior_melhor, confirmado, casas decimais)
TESTES = {
    "sprint_10": ("Sprint 10 m", "s", False, True, 2),
    "sprint_20": ("Sprint 20 m", "s", False, True, 2),
    "illinois": ("Agilidade (Illinois)", "s", False, True, 2),
    "saltos_vert_countermovement": ("Salto vertical (contramovimento)", "cm", True, True, 1),
    "saltos_vert_abalakov": ("Salto vertical (Abalakov)", "cm", True, True, 1),
    "single_hop": ("Single hop (salto horizontal)", "cm", True, True, 0),
    "teste_vo2_distancia_total": ("VO2 (distância)", "m", True, False, 0),
    "banco_wells": ("Banco de Wells (flexibilidade)", "cm", True, True, 1),
    "estabilidade_aquabag": ("Estabilidade Aquabag", "desequilibrios", False, False, 0),
    "blazepod_vel_reacao_ms": ("Blazepod (reação, tempo)", "ms", False, True, 0),
    "antropometria_altura": ("Altura", "cm", None, True, 0),
    "antropometria_peso": ("Peso", "kg", None, True, 1),
    # One to One (ficha da AP1: FIN, RES, POT, FSU, COR, MOB)
    "cadeira_isometrica": ("Cadeira isométrica (força de inferiores)", "s", True, True, 0),
    "flexao_bracos": ("Flexão de braços em 1 min", "repetições", True, True, 0),
    "prancha_ventral": ("Prancha ventral (core)", "s", True, True, 0),
}
BATERIA_PKZ = ["sprint_10", "sprint_20", "illinois", "saltos_vert_countermovement", "saltos_vert_abalakov", "single_hop",
               "teste_vo2_distancia_total", "banco_wells", "estabilidade_aquabag", "blazepod_vel_reacao_ms",
               "antropometria_altura", "antropometria_peso"]
BATERIA_OTO = ["cadeira_isometrica", "teste_vo2_distancia_total", "saltos_vert_countermovement", "flexao_bracos",
               "prancha_ventral", "banco_wells", "antropometria_altura", "antropometria_peso"]


def _crianca(idade: float, aos8: float, aos16: float) -> float:
    """Interpola entre o típico aos 8 e aos 16 anos; acima de 16 cresce bem pouco até os 18."""
    if idade <= 16:
        return aos8 + (aos16 - aos8) * (idade - 8) / 8
    return aos16 + (aos16 - aos8) / 8 * 0.5 * min(idade - 16, 2)


def tipico(teste: str, idade: float, sexo: str) -> float:
    f = sexo == "F"
    adulto = idade >= 18
    if teste == "sprint_10":
        return _crianca(idade, 2.45, 2.02) + (0.07 if f else 0)
    if teste == "sprint_20":
        return _crianca(idade, 4.35, 3.40) + (0.15 if f else 0)
    if teste == "illinois":
        return _crianca(idade, 21.2, 17.3) + (0.9 if f else 0)
    if teste == "saltos_vert_countermovement":
        if adulto:
            return 27 if f else 37
        return _crianca(idade, 19, 36) - (3.5 if f and idade >= 12 else 1 if f else 0)
    if teste == "saltos_vert_abalakov":
        return tipico("saltos_vert_countermovement", idade, sexo) * 1.12
    if teste == "single_hop":
        return _crianca(idade, 98, 178) - (12 if f and idade >= 12 else 4 if f else 0)
    if teste == "teste_vo2_distancia_total":
        if adulto:
            return 1900 if f else 2300
        return _crianca(idade, 1150, 2150) - (180 if f and idade >= 12 else 60 if f else 0)
    if teste == "banco_wells":
        return (24 if adulto else _crianca(idade, 22, 27)) + (5 if f else 0)
    if teste == "estabilidade_aquabag":
        return max(1.0, _crianca(idade, 7, 2.5))
    if teste == "blazepod_vel_reacao_ms":
        return _crianca(idade, 790, 540)
    if teste == "antropometria_altura":
        if adulto:
            return 164 if f else 177
        return _crianca(idade, 128, 172) - (6 if f and idade >= 14 else 0)
    if teste == "antropometria_peso":
        if adulto:
            return 62 if f else 78
        return _crianca(idade, 27, 60) - (5 if f and idade >= 14 else 0)
    if teste == "cadeira_isometrica":
        return (85 if adulto else _crianca(idade, 38, 75)) - (6 if f else 0)
    if teste == "flexao_bracos":
        return (20 if f else 32) if adulto else _crianca(idade, 10, 28) - (6 if f and idade >= 12 else 2 if f else 0)
    if teste == "prancha_ventral":
        return 100 if adulto else _crianca(idade, 40, 95)
    raise KeyError(teste)


# Quanto o nível do aluno mexe em cada teste (em fração do típico) e a variação própria do teste.
ESPALHAMENTO = {"sprint_10": .05, "sprint_20": .05, "illinois": .05, "saltos_vert_countermovement": .13,
                "saltos_vert_abalakov": .13, "single_hop": .09, "teste_vo2_distancia_total": .11, "banco_wells": .22,
                "estabilidade_aquabag": .35, "blazepod_vel_reacao_ms": .08, "antropometria_altura": .03,
                "antropometria_peso": .12, "cadeira_isometrica": .2, "flexao_bracos": .22, "prancha_ventral": .22}
GANHO_POR_AVALIACAO = {"sprint_10": .015, "sprint_20": .018, "illinois": .015, "saltos_vert_countermovement": .04,
                       "saltos_vert_abalakov": .04, "single_hop": .03, "teste_vo2_distancia_total": .04,
                       "banco_wells": .03, "estabilidade_aquabag": .15, "blazepod_vel_reacao_ms": .025,
                       "cadeira_isometrica": .08, "flexao_bracos": .08, "prancha_ventral": .09}


def arredondar(teste: str, valor: float):
    casas = TESTES[teste][4]
    if teste in ("sprint_10", "sprint_20", "illinois"):
        valor = round(valor * 100) / 100
    v = round(valor, casas)
    return int(v) if casas == 0 else v


def valor_do_teste(aluno: dict, teste: str, idade: float, ordem: int, sorte_teste: dict) -> float:
    base = tipico(teste, idade, aluno["sexo"])
    _, _, maior_melhor, _, _ = TESTES[teste]
    z = 0.65 * aluno["nivel"] + 0.75 * sorte_teste.setdefault(teste, sorte.gauss(0, 1))
    espalha = ESPALHAMENTO[teste]
    if maior_melhor is None:
        return base * (1 + espalha * sorte_teste.setdefault(teste + "_corpo", sorte.gauss(0, 1)))
    sentido = 1 if maior_melhor else -1
    ganho = GANHO_POR_AVALIACAO[teste] * ordem * (1 + 0.6 * sorte.gauss(0, 1))
    ruido = sorte.gauss(0, 0.012 if espalha < .1 else 0.03)
    return max(0.0, base * (1 + sentido * (espalha * z + ganho + ruido)))


# ---------------------------------------------------------------- alunos
CATEGORIAS = [(8, "sub_9"), (10, "sub_11"), (12, "sub_13"), (14, "sub_15"), (16, "sub_17")]


def categoria_da_idade(idade: int) -> str:
    return next(c for limite, c in CATEGORIAS if idade <= limite)


# 6 modalidades × 7 alunos. Idades espalhadas para cada modalidade ter gente nas três faixas da PKZ.
MODALIDADES = ["Futebol de campo", "Futsal", "Basquete", "Vôlei", "Natação", "Hipismo"]
IDADES_PKZ = [8, 9, 10, 11, 12, 13, 15]
IDADES_OTO = [7, 8, 9, 9, 10, 10, 11, 11, 12, 12, 12, 13, 14, 14, 15, 16, 16, 17, 19, 21, 24, 27, 29, 32, 35, 38, 41, 45]
# Datas das avaliações: trimestrais; a última de cada aluno cai em datas diferentes para a reavaliação ter os três casos.
CALENDARIO = [date(2026, 2, 9), date(2026, 5, 11), date(2026, 8, 3)]
ULTIMAS = [date(2026, 8, 3), date(2026, 8, 24), date(2026, 9, 21), date(2026, 10, 19), date(2026, 11, 3)]

alunos: list[dict] = []
for modalidade in MODALIDADES:
    idades = IDADES_PKZ[:]
    sorte.shuffle(idades)
    for i, idade in enumerate(idades):
        sexo = "F" if (modalidade in ("Vôlei", "Natação", "Hipismo") and i % 2 == 0) or (i % 4 == 3) else "M"
        alunos.append({"unidade": "PKZ", "modalidade": modalidade, "idade": idade, "sexo": sexo})
for i, idade in enumerate(IDADES_OTO):
    alunos.append({"unidade": "ONE_TO_ONE", "modalidade": None, "idade": idade, "sexo": "F" if i % 2 else "M"})

for n, a in enumerate(alunos):
    a["atleta_id"] = novo_id()
    a["nome"] = novo_nome(a["sexo"])
    a["nivel"] = max(-2.2, min(2.2, sorte.gauss(0, 1)))
    a["categoria"] = categoria_da_idade(a["idade"]) if a["unidade"] == "PKZ" else None
    a["entrada_em"] = (date(2024, 2, 1) + timedelta(days=sorte.randrange(0, 900))).isoformat()
    # Quantas avaliações: PKZ de 0 a 4 (um aluno novo por modalidade); One to One de 1 a 3, nunca zero.
    if a["unidade"] == "PKZ":
        posicao = n % 7
        a["n_avaliacoes"] = 0 if posicao == 6 and a["modalidade"] in ("Futsal", "Natação") else [1, 2, 3, 3, 4, 2, 3][posicao]
    else:
        a["n_avaliacoes"] = [1, 2, 3, 2][n % 4]
    a["ativo"] = True

# Inativos: dois da PKZ e dois do One to One, todos com avaliação, para o botão "Incluir inativos" ter efeito.
for a in [alunos[5], alunos[23], alunos[45], alunos[58]]:
    a["ativo"] = False

# ---------------------------------------------------------------- avaliações
evolucao: list[dict] = []
comparacao: list[dict] = []
for a in alunos:
    if not a["n_avaliacoes"]:
        a["ultima"] = None
        continue
    ultima = ULTIMAS[sorte.randrange(len(ULTIMAS))] if a["ativo"] else date(2026, 5, 11)
    datas = [d for d in CALENDARIO if d < ultima - timedelta(days=45)][-(a["n_avaliacoes"] - 1):] if a["n_avaliacoes"] > 1 else []
    datas = sorted(set(datas + [ultima]))[-a["n_avaliacoes"]:]
    a["ultima"] = datas[-1]
    bateria = BATERIA_PKZ if a["unidade"] == "PKZ" else BATERIA_OTO
    sorte_teste: dict = {}
    # Alguns alunos não fizeram um teste: o cartão mostra "sem dado" nesse atributo.
    pulado = {"estabilidade_aquabag"} if a["nome"].startswith(("Caio", "Lara")) else set()
    assimetria = 0.12 if a["nome"].startswith(("Murilo", "Elisa", "Igor")) else abs(sorte.gauss(0, 0.03))
    for ordem, data in enumerate(datas):
        idade_no_dia = a["idade"] - (HOJE - data).days / 365.25
        avaliacao_id = novo_id()
        for teste in bateria:
            if teste in pulado:
                continue
            nome, unidade, maior_melhor, confirmado, _ = TESTES[teste]
            v = valor_do_teste(a, teste, idade_no_dia, ordem, sorte_teste)
            lados = [("dir", v * (1 + assimetria / 2)), ("esq", v * (1 - assimetria / 2))] if teste == "single_hop" else [(None, v)]
            for lado, valor in lados:
                evolucao.append({"atleta_id": a["atleta_id"], "avaliacao_id": avaliacao_id, "data_avaliacao": data.isoformat(),
                                 "teste": teste, "teste_nome": nome, "lado": lado, "unidade_medida": unidade,
                                 "maior_melhor": maior_melhor, "confirmado": confirmado, "valor": arredondar(teste, valor),
                                 "tentativas_validas": 1 if teste.startswith("antropometria") else 3})

    # Comparação: última contra a anterior, pela regra da view (2% = estável).
    linhas = [l for l in evolucao if l["atleta_id"] == a["atleta_id"]]
    datas_feitas = sorted({l["data_avaliacao"] for l in linhas})
    if len(datas_feitas) < 2:
        continue
    anterior, atual = datas_feitas[-2], datas_feitas[-1]
    for l in [l for l in linhas if l["data_avaliacao"] == atual]:
        antes = next((x for x in linhas if x["data_avaliacao"] == anterior and x["teste"] == l["teste"] and x["lado"] == l["lado"]), None)
        if not antes:
            continue
        va, vb = float(antes["valor"]), float(l["valor"])
        pct = (vb - va) / abs(va) * 100 if va else None
        if l["maior_melhor"] is None:
            situacao = "sem_classificacao"
        elif va == vb or (pct is not None and abs(pct) < ESTAVEL_PCT):
            situacao = "estavel"
        else:
            situacao = "melhorou" if (vb > va) == l["maior_melhor"] else "piorou"
        comparacao.append({"atleta_id": a["atleta_id"], "teste": l["teste"], "teste_nome": l["teste_nome"], "lado": l["lado"],
                           "unidade_medida": l["unidade_medida"], "maior_melhor": l["maior_melhor"], "confirmado": l["confirmado"],
                           "data_anterior": anterior, "valor_anterior": antes["valor"], "data_atual": atual,
                           "valor_atual": l["valor"], "variacao_abs": round(vb - va, 2),
                           "variacao_pct": None if pct is None else round(pct, 1), "situacao": situacao})

# ---------------------------------------------------------------- presença e relatórios de treino
OBSERVACOES = ["Boa evolução na técnica de corrida; manter o trabalho de frequência de passada.",
               "Chegou cansado, treino adaptado com menos volume.",
               "Mostrou mais confiança nas mudanças de direção.",
               "Precisa reforçar o aquecimento de tornozelo antes dos saltos.",
               "Excelente foco nos exercícios de reação.",
               "Relatou leve desconforto no joelho; observar na próxima sessão.",
               "Cumpriu toda a série de força com boa execução.",
               "Melhorou o controle de tronco na prancha.", ""]
presenca: list[dict] = []
treino: list[dict] = []
inicio = HOJE - timedelta(weeks=10)
for a in alunos:
    dias = (0, 2) if a["unidade"] == "PKZ" else sorte.choice([(0, 3), (1, 3), (0, 2, 4)])
    hora = sorte.choice(["07:00:00", "08:30:00", "16:00:00", "17:30:00", "19:00:00"])
    assiduidade = min(0.98, max(0.6, 0.85 + 0.06 * a["nivel"] + sorte.gauss(0, 0.05)))
    if not a["ativo"]:
        continue
    dia = inicio
    while dia <= HOJE:
        if dia.weekday() in dias:
            if dia == HOJE:
                status = "agendado" if sorte.random() < .5 else "presente"
            elif sorte.random() < 0.03:
                status = "cancelado"
            else:
                status = "presente" if sorte.random() < assiduidade else "falta"
            presenca.append({"atleta_id": a["atleta_id"], "data": dia.isoformat(), "hora_inicio": hora, "status": status})
            if status == "presente" and dia < HOJE and sorte.random() < 0.35:
                treino.append({"atleta_id": a["atleta_id"], "relatorio_id": novo_id(), "data": dia.isoformat(),
                               "tipo_treino": "força" if a["unidade"] == "ONE_TO_ONE" else "físico",
                               "observacoes": sorte.choice(OBSERVACOES) or None})
        dia += timedelta(days=1)

# ---------------------------------------------------------------- atleta (view api.atleta + campos que a API ainda não tem)
atletas = []
for a in sorted(alunos, key=lambda x: x["nome"]):
    datas = {l["data_avaliacao"] for l in evolucao if l["atleta_id"] == a["atleta_id"]}
    atletas.append({"atleta_id": a["atleta_id"], "unidade": a["unidade"], "nome": a["nome"], "idade": a["idade"],
                    "categoria": a["categoria"], "ativo": a["ativo"], "total_avaliacoes": len(datas),
                    "ultima_avaliacao_em": max(datas) if datas else None,
                    # Ainda não existem na API; a cópia de teste usa para o filtro e para a apresentação.
                    "modalidade": a["modalidade"], "sexo": a["sexo"], "entrada_em": a["entrada_em"]})

SAIDA.mkdir(parents=True, exist_ok=True)
for nome, linhas in (("atleta", atletas), ("evolucao", evolucao), ("comparacao", comparacao), ("presenca", presenca), ("treino", treino)):
    (SAIDA / f"{nome}.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nome}.json: {len(linhas)} linhas")
