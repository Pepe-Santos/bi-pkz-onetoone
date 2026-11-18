"""Relatórios v2 (PKZ e One to One): 3 páginas no semanal, 4 no mensal e 5 no anual.

Fluxo: contrato de dados (JSON) -> validação -> indicadores -> páginas (HTML) -> PDF A4.
Os dados vêm da API, de CSVs ou de um JSON preenchido à mão, sempre no mesmo contrato
(veja relatorios/RELATORIOS_V2.md). Nenhum número é escrito no código: tudo é calculado
a partir dos registros do contrato.
"""
PAGINAS = {"semanal": 3, "mensal": 4, "anual": 5}
