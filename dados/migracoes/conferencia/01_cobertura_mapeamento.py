#!/usr/bin/env python3
"""
conferencia/01_cobertura_mapeamento.py — cobertura do mapeamento (tarefa 1.3)

Compara as colunas reais do banco (information_schema) com os CSVs de
mapeamento/ e classifica cada coluna. Só lê: não grava nada no banco.

  ORIGEM (as 28 tabelas de `origem`): cada coluna precisa aparecer em pelo
  menos uma linha do mapeamento, como fonte de uma coluna do destino ou numa
  decisão de não migrar.
      direta       citada só em linhas cuja transformação começa com "direto"
      transformada citada em pelo menos uma linha com outra transformação
      nao_migrada  citada só em linhas de decisão de não migrar (tabela_destino = —)
      SEM_DECISAO  não aparece em nenhuma linha  → erro

  DESTINO (tabelas de `novo`, sem as de controle da carga `carga_*`): cada
  coluna precisa ter pelo menos uma linha no mapeamento.
      direta       todas as linhas dela começam com "direto"
      transformada alguma linha tem origem e outra transformação
      gerada       nenhuma linha tem origem (calculada na carga: id novo, now(), pendência...)
      SEM_LINHA    nenhuma linha  → erro
  (uma coluna com linhas de classes diferentes, por exemplo `avaliacao.tipo`,
   que é gerada no script 60 e no 70, recebe a classe mais forte:
   transformada > direta > gerada.)

  Também acusa: coluna de destino no CSV que não existe em `novo` e coluna de
  origem citada no CSV que não existe em `origem`.

Uso (da pasta dados/migracoes):
  1) Direto no banco, com o psql no PATH e a conexão em ENSAIO_URL (ver README):
       python conferencia/01_cobertura_mapeamento.py
  2) Sem psql: exporte as colunas para um CSV (schema,tabela,coluna) com
       select table_schema, table_name, column_name
       from information_schema.columns c
       join information_schema.tables t using (table_schema, table_name)
       where table_schema in ('origem', 'novo') and t.table_type = 'BASE TABLE'
       order by 1, 2, ordinal_position;
     e rode:
       python conferencia/01_cobertura_mapeamento.py --colunas colunas.csv
Opções:
  --detalhe arquivo.csv   grava a classe de cada coluna (uma linha por coluna)

Sai com código 1 se houver qualquer erro. Só usa a biblioteca padrão do Python 3.
O que conta como "citada": o campo `origem` do CSV no formato do
mapeamento/README.md (`origem.tabela.coluna`; várias separadas por `|`, e depois
da primeira `| coluna` é da mesma tabela; `origem.t.data.chave` = coluna `data`).
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
MAPEAMENTO = os.path.join(AQUI, "..", "mapeamento")
CABECALHO = ["tabela_destino", "coluna", "tipo", "origem", "transformacao", "regra_pendencia_ou_rejeicao"]
SQL_COLUNAS = """
select c.table_schema, c.table_name, c.column_name
from information_schema.columns c
join information_schema.tables t using (table_schema, table_name)
where c.table_schema in ('origem', 'novo') and t.table_type = 'BASE TABLE'
order by 1, 2, c.ordinal_position
"""
FORCA = {"transformada": 3, "direta": 2, "gerada": 1}


def ler_colunas(args):
    if args.colunas:
        with open(args.colunas, encoding="utf-8-sig", newline="") as f:
            linhas = [r[:3] for r in csv.reader(f) if r]
        if linhas and linhas[0][0].strip().lower() in ("schema", "table_schema"):
            linhas = linhas[1:]
    else:
        url = os.environ.get("ENSAIO_URL")
        if not url:
            sys.exit("Defina ENSAIO_URL (ver README) ou use --colunas arquivo.csv")
        saida = subprocess.run(["psql", url, "-At", "-F", ",", "-c", SQL_COLUNAS],
                               capture_output=True, text=True, check=True).stdout
        linhas = [l.split(",") for l in saida.splitlines() if l.strip()]
    origem, destino = set(), set()
    for schema, tabela, coluna in linhas:
        schema, tabela, coluna = schema.strip(), tabela.strip(), coluna.strip()
        if schema == "origem":
            origem.add(f"{tabela}.{coluna}")
        elif schema == "novo" and not tabela.startswith("carga_"):
            destino.add(f"{tabela}.{coluna}")
    return origem, destino


def colunas_citadas(texto, origem, tabelas_origem):
    """'origem.t.c | c2 | origem.t2.c3' -> {t.c, t.c2, t2.c3}"""
    achou, ultima = set(), None
    for parte in re.split(r"\s*[|+]\s*|,\s*|\s/\s", texto or ""):
        parte = parte.strip()
        m = re.match(r"origem\.(\w+)\.(\w+)", parte)
        if m:
            ultima = m.group(1)
            achou.add(f"{m.group(1)}.{m.group(2)}")
            continue
        m = re.match(r"origem\.(\w+)\b", parte)
        if m and m.group(1) in tabelas_origem:
            ultima = m.group(1)
            continue
        m = re.match(r"(\w+)\.(\w+)", parte)
        if m and m.group(1) in tabelas_origem:
            ultima = m.group(1)
            achou.add(f"{m.group(1)}.{m.group(2)}")
            continue
        m = re.match(r"^(\w+)\b", parte)
        if m and ultima and f"{ultima}.{m.group(1)}" in origem:
            achou.add(f"{ultima}.{m.group(1)}")
    return achou


def classe_linha(row):
    if row["tabela_destino"].strip() == "—":
        return "nao_migrada"
    if not row["origem"].strip():
        return "gerada"
    if row["transformacao"].strip().lower().startswith("direto"):
        return "direta"
    return "transformada"


def main():
    p = argparse.ArgumentParser(description="Cobertura do mapeamento origem → novo")
    p.add_argument("--colunas", help="CSV schema,tabela,coluna exportado do information_schema")
    p.add_argument("--detalhe", help="grava a classe de cada coluna neste CSV")
    args = p.parse_args()

    origem, destino = ler_colunas(args)
    tabelas_origem = {o.split(".")[0] for o in origem}
    erros = []
    classes_origem = defaultdict(set)   # origem t.c -> classes das linhas que a citam
    classes_destino = defaultdict(set)  # destino t.c -> classes das linhas dela
    linhas = 0

    for arq in sorted(glob.glob(os.path.join(MAPEAMENTO, "*.csv"))):
        nome = os.path.basename(arq)
        if nome == "avaliacao_metricas.csv":   # catálogo de métricas, não é de/para de coluna
            continue
        with open(arq, encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            if r.fieldnames != CABECALHO:
                erros.append(f"{nome}: cabeçalho diferente de {CABECALHO}")
                continue
            for i, row in enumerate(r, 2):
                linhas += 1
                cl = classe_linha(row)
                t, c = row["tabela_destino"].strip(), row["coluna"].strip()
                if cl != "nao_migrada":
                    if f"{t}.{c}" not in destino:
                        erros.append(f"{nome}:{i} coluna de destino inexistente em novo: {t}.{c}")
                    classes_destino[f"{t}.{c}"].add(cl)
                citadas = colunas_citadas(row["origem"], origem, tabelas_origem)
                if cl == "nao_migrada" and not citadas:
                    erros.append(f"{nome}:{i} decisão de não migrar sem coluna de origem reconhecível")
                for o in citadas:
                    if o not in origem:
                        erros.append(f"{nome}:{i} coluna de origem inexistente: {o}")
                    classes_origem[o].add(cl)

    def classe_origem(o):
        cls = classes_origem.get(o)
        if not cls:
            return "SEM_DECISAO"
        if "transformada" in cls or "gerada" in cls:
            return "transformada"
        if "direta" in cls:
            return "direta"
        return "nao_migrada"

    def classe_destino(d):
        cls = classes_destino.get(d)
        if not cls:
            return "SEM_LINHA"
        return max(cls, key=FORCA.get)

    res_o = {o: classe_origem(o) for o in sorted(origem)}
    res_d = {d: classe_destino(d) for d in sorted(destino)}
    for o, cl in res_o.items():
        if cl == "SEM_DECISAO":
            erros.append(f"origem sem destino nem decisão de não migrar: {o}")
    for d, cl in res_d.items():
        if cl == "SEM_LINHA":
            erros.append(f"destino sem linha no mapeamento: {d}")

    print(f"Linhas lidas do mapeamento: {linhas}")
    print(f"\nORIGEM: {len(origem)} colunas em {len(tabelas_origem)} tabelas")
    for cl, n in sorted(Counter(res_o.values()).items()):
        print(f"  {cl:<13} {n}")
    tabelas_destino = {d.split('.')[0] for d in destino}
    print(f"\nDESTINO: {len(destino)} colunas em {len(tabelas_destino)} tabelas (sem carga_*)")
    for cl, n in sorted(Counter(res_d.values()).items()):
        print(f"  {cl:<13} {n}")
    print(f"\nERROS: {len(erros)}")
    for e in erros:
        print("  " + e)

    if args.detalhe:
        with open(args.detalhe, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["lado", "tabela", "coluna", "classe"])
            for o, cl in res_o.items():
                w.writerow(["origem", *o.split(".", 1), cl])
            for d, cl in res_d.items():
                w.writerow(["destino", *d.split(".", 1), cl])
        print(f"\nDetalhe por coluna gravado em {args.detalhe}")

    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
