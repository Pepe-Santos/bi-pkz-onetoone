"""Dados 100% sintéticos para testar os relatórios HTML (nenhum dado real de atleta)."""
from datetime import date, timedelta

REFERENCIA = date(2026, 8, 26)  # quarta-feira; semana 24/08 a 30/08/2026

PKZ_ID = "sintetico-pkz-0001"
O2O_ID = "sintetico-o2o-0001"

TESTES = [
    # codigo, nome, lado, unidade, maior_melhor, [(data, valor, confirmado)]
    ("sprint_20", "Sprint 20 m", None, "s", False,
     [("2026-03-10", 3.60, True), ("2026-05-22", 3.45, True), ("2026-08-25", 3.30, True)]),
    ("salto_cmj", "Salto vertical", None, "cm", True,
     [("2026-03-10", 30.0, True), ("2026-05-22", 33.5, True), ("2026-08-25", 35.0, True)]),
    ("agilidade_t", "Agilidade em T", None, "s", False,
     [("2026-03-10", 11.2, True), ("2026-05-22", 11.0, True), ("2026-08-25", 11.5, True)]),
    ("forca_preensao", "Força de preensão", "dir", "kg", True,
     [("2026-03-10", 20.0, True), ("2026-05-22", 21.0, True), ("2026-08-25", 21.0, True)]),
    ("forca_preensao", "Força de preensão", "esq", "kg", True,
     [("2026-03-10", 18.0, True), ("2026-05-22", 19.0, True), ("2026-08-25", 20.0, True)]),
    ("flexibilidade", "Flexibilidade", None, "cm", True,
     [("2026-05-22", 14.0, True), ("2026-08-25", 15.0, False)]),  # último em validação
]


def pkz_sintetico():
    atleta = {
        "atleta_id": PKZ_ID, "unidade": "PKZ", "nome": "Atleta Exemplo Sintético",
        "idade": 12, "categoria": "Sub-13", "ativo": True,
    }
    evolucoes = []
    ids = {"2026-03-10": "av-1", "2026-05-22": "av-2", "2026-08-25": "av-3"}
    for codigo, nome, lado, unidade, maior_melhor, medidas in TESTES:
        for data, valor, confirmado in medidas:
            evolucoes.append({
                "atleta_id": PKZ_ID, "avaliacao_id": ids[data], "data_avaliacao": data,
                "teste": codigo, "teste_nome": nome, "lado": lado, "unidade_medida": unidade,
                "maior_melhor": maior_melhor, "confirmado": confirmado, "valor": valor,
                "tentativas_validas": 3,
            })
    presencas = []
    inicio = date(2026, 2, 2)
    dia = inicio
    contador = 0
    while dia <= date(2026, 8, 31):
        if dia.weekday() in (0, 2, 4):  # seg, qua, sex
            contador += 1
            status = "falta" if contador % 7 == 0 else "cancelado" if contador % 11 == 0 else "presente"
            if dia > date(2026, 8, 26):
                status = "agendado"
            presencas.append({"atleta_id": PKZ_ID, "unidade": "PKZ", "data": dia.isoformat(),
                              "hora_inicio": "07:00:00", "status": status})
        dia += timedelta(days=1)
    return atleta, evolucoes, presencas


def o2o_sintetico():
    atleta = {"atleta_id": O2O_ID, "unidade": "ONE_TO_ONE", "nome": "Aluno Exemplo Sintético",
              "idade": 32, "ativo": True}
    tipos = ["Força inferiores", "Força superiores", "Potência", "Condicionamento"]
    intens = ["Moderada", "Alta", "Leve"]
    presencas, treinos = [], []
    dia = date(2026, 1, 5)
    n = 0
    while dia <= date(2026, 12, 18):
        if dia.weekday() in (0, 2, 4) and dia <= date(2026, 8, 26):
            n += 1
            status = "falta" if n % 9 == 0 else "cancelado" if n % 13 == 0 else "presente"
            presencas.append({"atleta_id": O2O_ID, "unidade": "ONE_TO_ONE", "data": dia.isoformat(),
                              "status": status})
            if status == "presente":
                treinos.append({
                    "atleta_id": O2O_ID, "unidade": "ONE_TO_ONE", "data": dia.isoformat(),
                    "tipo_treino": tipos[n % 4], "intensidade": intens[n % 3],
                    "objetivos": "Ganho de força geral" if n % 2 else "Melhorar condicionamento",
                    "desempenho": "Executou todas as séries" if n % 3 else None,
                })
        dia += timedelta(days=1)
    return atleta, presencas, treinos
