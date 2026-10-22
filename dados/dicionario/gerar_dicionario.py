#!/usr/bin/env python3
"""
dicionario/gerar_dicionario.py — dicionário de dados do schema novo (tarefa 3.5)

Junta três fontes e escreve um arquivo por domínio em dados/dicionario/:

  1. estrutura do banco (information_schema e catálogo): tabela, coluna, tipo,
     obrigatoriedade, padrão, chave primária, chave estrangeira, comentário e,
     nas colunas categóricas, a lista de valores que existem hoje;
  2. mapeamento/*.csv (tarefa 1.3): de onde a coluna vem na origem e como é
     transformada;
  3. classificação de sensibilidade, por regra (ver SENSIBILIDADE abaixo).

Só lê: não grava nada no banco.

Uso (da pasta dados/migracoes, como as conferências):
  1) Direto no banco, com psql no PATH e a conexão em ENSAIO_URL:
       python ../dicionario/gerar_dicionario.py
  2) Sem psql, a partir de um JSON exportado antes:
       python ../dicionario/gerar_dicionario.py --entrada estrutura.json

O formato do JSON está em FORMATO_ENTRADA, no fim deste arquivo.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MIGRACOES = AQUI.parent / "migracoes"
MAPEAMENTO = MIGRACOES / "mapeamento"

# Os 6 domínios do modelo conceitual, na ordem das migrations.
DOMINIOS = [
    ("00-infra-carga", "Infraestrutura de carga", "001",
     ["carga_execucao", "carga_rejeitado", "carga_gabarito"]),
    ("01-cadastro", "Cadastro e identidade", "002",
     ["unidade", "servico", "configuracao_unidade", "pessoa", "perfil_usuario", "papel",
      "papel_usuario", "aluno", "aluno_servico", "responsavel_aluno", "profissional",
      "profissional_servico"]),
    ("02-comercial", "Comercial e créditos", "003",
     ["plano", "plano_beneficio", "matricula", "renovacao", "credito_lancamento"]),
    ("03-agenda-treino", "Agenda e treino", "004 e 005",
     ["horario_grade", "bloqueio_agenda", "bloqueio_grade", "agendamento", "sessao_treino",
      "lista_espera", "feedback_treino", "catalogo_item", "relatorio_treino", "relatorio_item"]),
    ("04-avaliacao", "Avaliação e testes físicos", "006",
     ["metrica", "avaliacao", "avaliacao_medida"]),
    ("05-atendimento", "Atendimento especializado", "007",
     ["atendimento", "evolucao", "anamnese"]),
    ("06-documentos", "Documentos, conformidade e comunicação", "008",
     ["arquivo", "consentimento", "relatorio_emissao", "relatorio_envio", "notificacao",
      "evento_auditoria", "acesso_dado_sensivel"]),
]

# Classificação de sensibilidade. A primeira regra que casar vale.
# Revisada pela Frente 3; é o que a política de acesso (012) usa como critério.
SENSIBILIDADE = [
    ("clinico", {
        "tabelas": {"anamnese", "atendimento", "evolucao"},
        "colunas": {"dor", "dor_local", "dor_intensidade", "dor_movimento", "confidencialidade"},
    }),
    ("pessoal", {
        "tabelas": set(),
        "colunas": {"nome", "cpf", "telefone", "email", "username", "foto_url", "data_nascimento",
                    "endereco", "avaliador_nome", "registro_conselho"},
    }),
    ("tecnico", {
        "tabelas": {"carga_execucao", "carga_rejeitado", "carga_gabarito"},
        "colunas": {"id", "criado_em", "atualizado_em", "pendencia", "id_origem", "origem_tabela",
                    "origem_id", "tabela_origem"},
    }),
]


# Significado das colunas que seguem padrão do grupo (CONVENCOES 3). O resto fica
# como [revisar]: é o que precisa de quem conhece a regra de negócio.
SIGNIFICADO_EXATO = {
    "id": "Chave primária.",
    "criado_em": "Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe.",
    "atualizado_em": "Última atualização; o `on conflict do update` grava `now()`.",
    "pendencia": "Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga.",
    "id_origem": "Id da linha na origem, usado para reexecutar a carga sem duplicar.",
    "origem_tabela": "Tabela da origem de onde o registro veio.",
    "origem_id": "Id do registro na tabela de origem.",
    "tabela_origem": "Tabela da origem que gerou a linha.",
    "ativo": "Se o registro está ativo.",
    "codigo": "Código curto e estável, usado nas regras e nos scripts.",
    "nome": "Nome de exibição.",
    "ordem": "Ordem de exibição na tela.",
    "observacao": "Texto livre escrito por quem registrou.",
    "observacoes": "Texto livre escrito por quem registrou.",
    "data": "Data a que o registro se refere.",
    "hora_inicio": "Hora de início.",
    "hora_fim": "Hora de término.",
    "status": "Situação do registro.",
    "unidade_id": "Unidade (PKZ ou One to One) a que o registro pertence.",
    "servico_id": "Serviço a que o registro se refere.",
    "aluno_id": "Aluno a que o registro se refere.",
    "pessoa_id": "Pessoa a que o registro se refere.",
    "usuario_id": "Usuário de login dono do registro.",
    "profissional_id": "Profissional responsável pelo registro.",
    "criado_por": "Usuário que criou o registro na origem.",
    "agendamento_id": "Agendamento que originou o registro.",
    "avaliacao_id": "Avaliação a que o registro pertence.",
    "atendimento_id": "Atendimento a que o registro pertence.",
    "relatorio_id": "Relatório a que o registro pertence.",
    "matricula_id": "Matrícula a que o registro pertence.",
    "plano_id": "Plano contratado.",
    "papel_id": "Papel do usuário.",
    "metrica_id": "Métrica medida.",
    "catalogo_item_id": "Item de catálogo que classifica o registro.",
    "arquivo_id": "Arquivo ligado ao registro.",
    "emissao_id": "Emissão de relatório a que o envio pertence.",
    "script": "Nome do domínio do script de carga que gerou a linha.",
    "confidencialidade": "Nível de sigilo: define quem pode ler (política 012).",
}


def significado_padrao(coluna):
    if coluna in SIGNIFICADO_EXATO:
        return SIGNIFICADO_EXATO[coluna]
    if coluna.endswith("_em"):
        return "Data e hora do evento que o nome indica."
    if coluna.endswith("_id"):
        return "Chave estrangeira; ver a coluna Chave."
    return None


def classificar(tabela, coluna):
    for nivel, regra in SENSIBILIDADE:
        if tabela in regra["tabelas"] or coluna in regra["colunas"]:
            return nivel
    return "operacional"


def ler_mapeamento():
    """De/para por (tabela_destino, coluna), vindo dos CSVs da tarefa 1.3."""
    de_para = defaultdict(list)
    if not MAPEAMENTO.is_dir():
        return de_para
    for arquivo in sorted(MAPEAMENTO.glob("*.csv")):
        with arquivo.open(encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                destino = (linha.get("tabela_destino") or "").strip()
                coluna = (linha.get("coluna") or "").strip()
                if not destino or destino == "—" or not coluna:
                    continue
                de_para[(destino, coluna)].append({
                    "origem": (linha.get("origem") or "").strip(),
                    "transformacao": (linha.get("transformacao") or "").strip(),
                    "regra": (linha.get("regra_pendencia_ou_rejeicao") or "").strip(),
                })
    return de_para


CONSULTAS = {
    "tabelas": """
        select c.relname as tabela, obj_description(c.oid,'pg_class') as comentario,
          substring(query_to_xml(format('select count(*) as n from novo.%I', c.relname),
                    false, true, '')::text from '<n>(\\d+)</n>')::bigint as linhas
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname='novo' and c.relkind='r' order by 1""",
    "colunas": """
        select c.relname as tabela, a.attname as coluna,
          format_type(a.atttypid, a.atttypmod) as tipo, a.attnotnull as obrigatoria,
          pg_get_expr(ad.adbin, ad.adrelid) as padrao, col_description(a.attrelid, a.attnum) as comentario,
          exists (select 1 from pg_constraint k where k.conrelid=c.oid and k.contype='p'
                   and a.attnum = any(k.conkey)) as pk,
          (select string_agg(k.confrelid::regclass::text, ', ') from pg_constraint k
            where k.conrelid=c.oid and k.contype='f' and a.attnum = any(k.conkey)) as fk
        from pg_class c join pg_namespace n on n.oid=c.relnamespace
        join pg_attribute a on a.attrelid=c.oid and a.attnum>0 and not a.attisdropped
        left join pg_attrdef ad on ad.adrelid=c.oid and ad.adnum=a.attnum
        where n.nspname='novo' and c.relkind='r' order by c.relname, a.attnum""",
}


def ler_do_banco():
    url = os.environ.get("ENSAIO_URL")
    if not url:
        sys.exit("Defina ENSAIO_URL (ver ../migracoes/README.md) ou use --entrada estrutura.json")
    dados = {}
    for nome, sql in CONSULTAS.items():
        saida = subprocess.run(
            ["psql", url, "-At", "-F", "\t", "-c", sql],
            capture_output=True, text=True, check=True).stdout
        dados[nome] = saida
    return dados


def marcar(texto):
    """Escapa o que quebraria a tabela markdown."""
    if texto is None or texto == "":
        return ""
    return str(texto).replace("|", "\\|").replace("\n", " ").strip()


def escrever(dados, de_para, saida_dir):
    tabelas = {t["tabela"]: t for t in dados["tabelas"]}
    colunas = defaultdict(list)
    for c in dados["colunas"]:
        colunas[c["tabela"]].append(c)
    valores = {(v["tabela"], v["coluna"]): v["valores"]
               for v in dados.get("valores", []) if v.get("valores")}

    cobertas = set()
    indice = []
    for arquivo, titulo, migration, lista in DOMINIOS:
        linhas = [f"# {titulo}", "",
                  f"> Dicionário de dados do schema `novo` · migration {migration} · gerado por "
                  f"`dicionario/gerar_dicionario.py`.",
                  "",
                  "Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), "
                  "`operacional` (rotina do negócio), `tecnico` (controle da carga).",
                  ""]
        for tabela in lista:
            if tabela not in tabelas:
                continue
            cobertas.add(tabela)
            meta = tabelas[tabela]
            linhas.append(f"## `{tabela}`")
            linhas.append("")
            if meta.get("comentario"):
                linhas.append(f"{meta['comentario']}")
                linhas.append("")
            linhas.append(f"Linhas no ensaio de 12/10: **{meta.get('linhas', 0)}**")
            linhas.append("")
            linhas.append("| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |")
            linhas.append("|---|---|---|---|---|---|---|---|---|")
            for c in colunas.get(tabela, []):
                chave = "PK" if c["pk"] else (f"FK → {c['fk']}" if c.get("fk") else "")
                mapas = de_para.get((tabela, c["coluna"]), [])
                origem = "; ".join(sorted({m["origem"] for m in mapas if m["origem"]})) or "—"
                transf = "; ".join(sorted({m["transformacao"] for m in mapas if m["transformacao"]}))
                if not transf and c.get("padrao"):
                    transf = f"padrão {c['padrao']}"
                significado = (c.get("comentario") or significado_padrao(c["coluna"]) or "[revisar]")
                linhas.append("| `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    c["coluna"], marcar(c["tipo"]), "sim" if c["obrigatoria"] else "não",
                    marcar(chave), marcar(origem), marcar(transf),
                    marcar(valores.get((tabela, c["coluna"]), "")),
                    classificar(tabela, c["coluna"]), marcar(significado)))
            linhas.append("")
        (saida_dir / f"{arquivo}.md").write_text("\n".join(linhas), encoding="utf-8")
        indice.append((arquivo, titulo, [t for t in lista if t in tabelas]))

    faltando = sorted(set(tabelas) - cobertas)
    return indice, faltando


FORMATO_ENTRADA = """
{"tabelas":[{"tabela":..,"comentario":..,"linhas":..}],
 "colunas":[{"tabela":..,"coluna":..,"tipo":..,"obrigatoria":..,"padrao":..,"comentario":..,"pk":..,"fk":..}],
 "valores":[{"tabela":..,"coluna":..,"valores":"a | b | c"}]}
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--entrada", help="JSON com a estrutura, no lugar de ler do banco")
    p.add_argument("--saida", default=str(AQUI), help="pasta de saída (padrão: dados/dicionario)")
    args = p.parse_args()

    dados = json.loads(Path(args.entrada).read_text(encoding="utf-8")) if args.entrada else ler_do_banco()
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    indice, faltando = escrever(dados, ler_mapeamento(), saida)

    total_colunas = len(dados["colunas"])
    revisar = sum(1 for c in dados["colunas"]
                  if not c.get("comentario") and not significado_padrao(c["coluna"]))
    print(f"{len(indice)} arquivos escritos em {saida}")
    print(f"{total_colunas} colunas; {revisar} ainda com significado [revisar]")
    if faltando:
        print("tabelas fora dos domínios:", ", ".join(faltando))


if __name__ == "__main__":
    main()
