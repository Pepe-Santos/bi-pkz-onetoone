#!/usr/bin/env python3
"""Gera a versão 2 do modelo conceitual (Chen) a partir dos DOTs originais.
Cada mudança feita na construção do banco (tarefas 1.2–1.7) entra em verde-azulado,
com o código M<n> que aparece na página "Registro de mudanças"."""
import os, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(BASE, "..", "fontes-dot")   # DOTs originais (13/10), não são alterados
OUT_DOT = BASE                                  # os DOTs v2 ficam nesta pasta
OUT_PDF = os.path.join(BASE, "pdf")
os.makedirs(OUT_PDF, exist_ok=True)
# Uso: python gerar_v2.py  (precisa do Graphviz: comando dot). A página de mudanças é mudancas.html.

V2_FILL, V2_COR, V2_REL = "#DCEFE7", "#2F7D62", "#E3F3EC"

# ---------------------------------------------------------------- construtores
def tag(texto, m):
    linhas = texto.split("\n")
    corpo = "<BR/>".join(linhas)
    return f'<{corpo}<BR/><FONT POINT-SIZE="8" COLOR="{V2_COR}"><B>{m}</B></FONT>>'

def ent(i, texto, m, nova=True, extra=""):
    fill = V2_FILL if nova else "#E4E0F5"
    return (f'  {i} [shape=box, style="filled,rounded", fillcolor="{fill}", color="{V2_COR}", '
            f'penwidth=2.2, label={tag(texto, m)}, margin="0.18,0.10"{extra}];\n')

def ent_existente(i, texto, tipo="proposta"):
    fill, cor = ("#E4E0F5", "#6B5FA8") if tipo == "proposta" else ("#EFEBE0", "#8A7F66")
    return (f'  {i} [shape=box, style="filled,rounded", fillcolor="{fill}", color="{cor}", penwidth=1.7, '
            f'label="{texto}", margin="0.18,0.10"];\n')

def rel(i, texto, m, ident=False):
    per = ", peripheries=2" if ident else ""
    return (f'  {i} [shape=diamond, style=filled, fillcolor="{V2_REL}", color="{V2_COR}", penwidth=1.6, '
            f'label={tag(texto, m)}, fontsize=10, margin="0.02,0.02"{per}];\n')

def attr(i, texto, chave=False, derivado=False):
    lab = f"<<U>{texto}</U>>" if chave else f'"{texto}"'
    est = "filled,dashed" if derivado else "filled,solid"
    return (f'  {i} [shape=ellipse, fillcolor="#FFFFFF", color="{V2_COR}", fontcolor="{V2_COR}", penwidth=1.2, '
            f'fontsize=9, label={lab}, height=0.30, margin="0.04,0.02", style="{est}"];\n')

def lig(a, b, card=None, validar=False):
    p = []
    if card:
        p.append(f'taillabel="{card}", labeldistance=2.6, labelangle=12, labelfontcolor="{V2_COR}"')
    p.append(f'color="{V2_COR}", penwidth=1.6')
    if validar:
        p.append("style=dashed")
    return f'  {a} -- {b} [{", ".join(p)}];\n'

def lig_attr(a, b):
    return f'  {a} -- {b} [color="{V2_COR}", penwidth=0.9];\n'

# ---------------------------------------------------------------- edição de texto
def troca(s, velho, novo, n=1):
    c = s.count(velho)
    assert c == n, f"esperava {n} ocorrência(s), achei {c}: {velho[:90]}"
    return s.replace(velho, novo)

def antes_do_fim(s, bloco):
    i = s.rstrip().rfind("}")
    return s[:i] + bloco + s[i:]

def subtitulo(s, novo):
    return re.sub(r'(<FONT POINT-SIZE="\d+" COLOR="#6A6A6A">).*?(</FONT>)',
                  lambda m: m.group(1) + novo + m.group(2), s, count=1, flags=re.S)

def destaca_no(s, no_id, m, texto=None, tracejado=False):
    """Contorno verde + código M num nó existente (entidade ou relacionamento)."""
    pat = re.compile(rf'^([ ]*){re.escape(no_id)} \[(.*)\];$', re.M)
    mt = pat.search(s)
    assert mt, no_id
    recuo, attrs = mt.group(1), mt.group(2)
    lab = re.search(r'label="((?:[^"\\]|\n)*)"', attrs, re.S)
    t = texto if texto is not None else lab.group(1)
    attrs = attrs.replace(lab.group(0), "label=" + tag(t, m))
    # garante cor do contorno (o primeiro 'color=' que não é fillcolor)
    attrs = re.sub(r'(?<!fill)color="#[0-9A-Fa-f]{6}"', f'color="{V2_COR}"', attrs)
    attrs = re.sub(r'penwidth=[\d.]+', 'penwidth=2.2', attrs)
    if tracejado:
        attrs = attrs.replace('style="filled,rounded"', 'style="filled,rounded,dashed"')
    return s[:mt.start()] + f"{recuo}{no_id} [{attrs}];" + s[mt.end():]

def recolore_aresta(s, origem_txt, nova_card=None):
    """Recolore uma aresta existente (linha exata sem o ';') e, se pedido, troca a cardinalidade."""
    linha = [l for l in s.split("\n") if l.strip().startswith(origem_txt)]
    assert len(linha) == 1, (origem_txt, len(linha))
    l = linha[0]
    novo = l.replace("[]", "[penwidth=1.1]")
    if nova_card:
        novo = re.sub(r'taillabel="[^"]*"', f'taillabel="{nova_card}"', novo)
    novo = re.sub(r'color="#[0-9A-Fa-f]{6}"', f'color="{V2_COR}"', novo)
    if f'color="{V2_COR}"' not in novo:
        novo = novo.replace("];", f', color="{V2_COR}"];')
    novo = novo.replace("];", f', penwidth=1.6, labelfontcolor="{V2_COR}"];') if "labelfontcolor" not in novo else novo
    return s.replace(l, novo)

def troca_attr(s, no_id, novo_texto):
    pat = re.compile(rf'^  {re.escape(no_id)} \[shape=ellipse.*$', re.M)
    mt = pat.search(s); assert mt, no_id
    linha = mt.group(0)
    novo = re.sub(r'label=(<<U>[^>]*</U>>|"[^"]*")', f'label="{novo_texto}"', linha)
    novo = novo.replace('color="#9A9A9A"', f'color="{V2_COR}", fontcolor="{V2_COR}"')
    s = s.replace(linha, novo)
    return s.replace(f"-- {no_id} [color=\"#A8A8A8\", penwidth=0.85]",
                     f"-- {no_id} [color=\"{V2_COR}\", penwidth=0.9]")

def ler(nome):
    return open(os.path.join(ORIG, nome), encoding="utf-8").read()

def gravar(nome, s):
    caminho = os.path.join(OUT_DOT, nome)
    open(caminho, "w", encoding="utf-8").write(s)
    return caminho

V2 = 'v2 (16/10/2026): em verde, o que mudou na construção do banco. Os códigos M remetem ao registro de mudanças.'

# ================================================================ 01 · Cadastro
s = ler("01-cadastro.dot")
s = subtitulo(s, "Quem é quem. Correção principal: Responsabilidade deixa de ser entidade e vira relacionamento N:M.<BR/>" + V2)
s = antes_do_fim(s,
    ent("CONFIG", "CONFIGURAÇÃO\nDA UNIDADE", "M1") +
    rel("R_configura", "configura", "M1") +
    attr("cf_prazo", "prazo_cancelamento") + attr("cf_cap", "capacidade_padrão") + attr("cf_cred", "créditos_padrão") +
    lig("UNIDADE", "R_configura", "(1,1)") + lig("R_configura", "CONFIG", "(1,1)") +
    lig_attr("CONFIG", "cf_prazo") + lig_attr("CONFIG", "cf_cap") + lig_attr("CONFIG", "cf_cred") +
    ent_existente("SERVICO", "SERVIÇO") +
    rel("R_podeagendar", "pode agendar", "M2") +
    lig("ATLETA", "R_podeagendar", "(0,N)") + lig("R_podeagendar", "SERVICO", "(0,N)") +
    ent_existente("PROF", "PROFISSIONAL") +
    rel("R_ehprof", "é", "M3") +
    lig("USUARIO", "R_ehprof", "(0,1)") + lig("R_ehprof", "PROF", "(1,1)")
)
gravar("01-cadastro.dot", s)

# ================================================================ 02 · Comercial
s = ler("02-comercial.dot")
s = subtitulo(s, "Matrícula é ternária e datada: é ela que dá histórico de plano e permite o atleta migrar de unidade. Saldo é derivado.<BR/>"
                 "Créditos são SESSÕES, não dinheiro, e não se acumulam: a renovação redefine o saldo (M6). O banco não guarda pagamento.<BR/>" + V2)
s = troca_attr(s, "a_saldo", "saldo: desde a última renovação · M6")
s = troca_attr(s, "l_qtd", "quantidade (na renovação = cota) · M6")
s = antes_do_fim(s,
    rel("R_pertence", "pertence a", "M4") +
    lig("UNIDADE", "R_pertence", "(0,N)") + lig("R_pertence", "PLANO", "(1,1)") +
    rel("R_renova", "renova", "M5") + rel("R_renserv", "refere-se a", "M5") +
    attr("r_per", "periodicidade") +
    lig("ATLETA:se", "R_renova", "(0,N)") + lig("R_renova", "RENOVACAO", "(1,1)") +
    lig("SERVICO:e", "R_renserv", "(0,N)") + lig("R_renserv", "RENOVACAO", "(1,1)") +
    lig_attr("RENOVACAO", "r_per") +
    ent_existente("AGEND", "AGENDAMENTO", "existe") +
    rel("R_debita", "debita", "M7") +
    lig("AGEND", "R_debita", "(0,N)", validar=True) + lig("R_debita", "LANC", "(0,1)", validar=True)
)
gravar("02-comercial.dot", s)

# ================================================================ 03 · Agenda
s = ler("03-agenda.dot")
s = subtitulo(s, "training_slots está morto (1 linha; slot_id nulo em 536/536). Disponibilidade vira grade + bloqueio.<BR/>"
                 "Item de Catálogo substitui as 7 dimensões de texto livre do relatório e os campos _other.<BR/>" + V2)
s = destaca_no(s, "R_oferece", "M8")
s = recolore_aresta(s, "R_oferece -- GRADE", "(0,1)")
s = destaca_no(s, "R_produz", "M13", texto="produz\n(só treino)")
s = troca_attr(s, "ag_dh", "data")
s = destaca_no(s, "AGEND", "M9")
s = antes_do_fim(s,
    attr("g_cap", "capacidade") + attr("g_int", "intervalo_min") +
    lig_attr("GRADE", "g_cap") + lig_attr("GRADE", "g_int") +
    attr("ag_hi", "hora_início") + attr("ag_hf", "hora_fim") +
    lig_attr("AGEND", "ag_hi") + lig_attr("AGEND", "ag_hf") +
    ent("LISTA", "LISTA DE\nESPERA", "M10") +
    rel("R_aguarda", "aguarda", "M10") + rel("R_paraLE", "para", "M10") +
    attr("le_data", "data_hora") + attr("le_st", "status") +
    lig("ATLETA", "R_aguarda", "(0,N)") + lig("R_aguarda", "LISTA", "(1,1)") +
    lig("SERVICO", "R_paraLE", "(0,N)") + lig("R_paraLE", "LISTA", "(1,1)") +
    lig_attr("LISTA", "le_data") + lig_attr("LISTA", "le_st") +
    rel("R_valeU", "vale para", "M11") + rel("R_valeS", "vale para", "M11") +
    lig("UNIDADE", "R_valeU", "(0,N)") + lig("R_valeU", "BLOQUEIO", "(0,1)") +
    lig("SERVICO", "R_valeS", "(0,N)") + lig("R_valeS", "BLOQUEIO", "(0,1)") +
    rel("R_sobreRel", "sobre", "M12") + rel("R_escreve", "escreve", "M12") +
    lig("ATLETA", "R_sobreRel", "(0,N)") + lig("R_sobreRel", "RELAT", "(1,1)") +
    lig("PROF", "R_escreve", "(0,N)", validar=True) + lig("R_escreve", "RELAT", "(0,1)", validar=True)
)
gravar("03-agenda.dot", s)

# ================================================================ 04 · Avaliação
s = ler("04-avaliacao.dot")
s = subtitulo(s, "Medida e Métrica são a lacuna crítica: sem elas não há gráfico de evolução. O catálogo já existe no código do app.<BR/>" + V2)
s = destaca_no(s, "R_aplica", "M15")
s = recolore_aresta(s, "R_aplica -- AVAL", "(0,1)")
s = troca(s, "{ rank=same; AVF; AVS; }", "{ rank=same; AVF; AVS; AVFISIO; }")
s = troca_attr(s, "mt_fx", "valor_mín / valor_máx")
s = troca_attr(s, "mt_sent", "direção_desejada")
s = troca_attr(s, "me_val", "valor_num / valor_texto")
s = destaca_no(s, "METRICA", "M18")
s = destaca_no(s, "MEDIDA", "M18")
s = antes_do_fim(s,
    ent("AVFISIO", "AVALIAÇÃO DE\nFISIOTERAPIA", "M14") +
    f'  SPEC -- AVFISIO [style=dashed, color="{V2_COR}", penwidth=1.6];\n' +
    rel("R_corrige", "corrige", "M16") +
    lig("AVAL:e", "R_corrige", "(0,1)") + lig("R_corrige", "AVAL:ne", "(0,1)") +
    ent_existente("UNIDADE", "UNIDADE") +
    rel("R_realizadaEm", "realizada em", "M17") +
    lig("UNIDADE", "R_realizadaEm", "(0,N)") + lig("R_realizadaEm", "AVAL", "(1,1)") +
    attr("mt_dom", "domínio") + attr("mt_lado", "usa_lado") + attr("mt_tipo", "tipo_dado") +
    lig_attr("METRICA", "mt_dom") + lig_attr("METRICA", "mt_lado") + lig_attr("METRICA", "mt_tipo") +
    ''
)
gravar("04-avaliacao.dot", s)

# ================================================================ 05 · Atendimento
s = ler("05-atendimento.dot")
s = subtitulo(s, "Anamnese sai de physio_assessments: é histórico clínico do atleta, não de um atendimento. Confidencialidade é decisão pendente.<BR/>"
                 "Nutrição, Psicologia e Fisioterapia ficam como o serviço do atendimento (não têm atributos próprios).<BR/>" + V2)
s = destaca_no(s, "ANAM", "M19")
s = destaca_no(s, "R_possuiA", "M19")
s = recolore_aresta(s, "ATLETA -- R_possuiA", "(0,N)")
s = antes_do_fim(s,
    ent_existente("AVAL", "AVALIAÇÃO DE\nFISIOTERAPIA") +
    rel("R_registradaEm", "registrada em", "M19") +
    lig("AVAL", "R_registradaEm", "(0,1)") + lig("R_registradaEm", "ANAM", "(1,1)") +
    ent_existente("AGEND", "AGENDAMENTO", "existe") +
    rel("R_atendidoEm", "atendido em", "M13") +
    lig("AGEND", "R_atendidoEm", "(0,N)", validar=True) + lig("R_atendidoEm", "ATEND", "(0,1)", validar=True) +
    ent_existente("USUARIO", "USUÁRIO", "existe") +
    rel("R_ehprof", "é", "M3") +
    lig("USUARIO", "R_ehprof", "(0,1)") + lig("R_ehprof", "PROF", "(1,1)")
)
gravar("05-atendimento.dot", s)

# ================================================================ 06 · Conformidade
s = ler("06-conformidade.dot")
s = subtitulo(s, "Emissão e Envio são o objetivo final do projeto e não existiam no modelo. Consentimento não existe no banco e a LGPD exige.<BR/>"
                 "Arquivo: relatório, avaliação e atendimento são exclusivos entre si; o atleta acompanha qualquer um deles (M20).<BR/>" + V2)
s = destaca_no(s, "R_anexa", "M20")
s = destaca_no(s, "HIST", "M21", texto="HISTÓRICO\n(derivado)", tracejado=True)
s = recolore_aresta(s, "R_regista -- HIST")
s = destaca_no(s, "R_executa", "M22")
s = recolore_aresta(s, "R_executa -- AUDIT", "(0,1)")
s = antes_do_fim(s,
    rel("R_enviado", "enviado por", "M20") +
    lig("USUARIO", "R_enviado", "(0,N)") + lig("R_enviado", "ARQUIVO", "(0,1)") +
    ent("ACESSO", "ACESSO A DADO\nSENSÍVEL", "M23") +
    rel("R_consulta", "consulta", "M23") + rel("R_sobreAc", "sobre", "M23") +
    attr("ac_ent", "entidade") + attr("ac_fin", "finalidade") + attr("ac_em", "acessado_em") +
    lig("USUARIO", "R_consulta", "(0,N)", validar=True) + lig("R_consulta", "ACESSO", "(1,1)", validar=True) +
    lig("ATLETA", "R_sobreAc", "(0,N)", validar=True) + lig("R_sobreAc", "ACESSO", "(0,1)", validar=True) +
    lig_attr("ACESSO", "ac_ent") + lig_attr("ACESSO", "ac_fin") + lig_attr("ACESSO", "ac_em") +
    rel("R_geraArq", "gera", "M24") +
    lig("EMISSAO", "R_geraArq", "(0,1)") + lig("R_geraArq", "ARQUIVO", "(0,N)")
)
gravar("06-conformidade.dot", s)

# ================================================================ 00 · Visão geral
s = ler("00-visao-geral.dot")
s = subtitulo(s, "v2 (16/10/2026): 39 entidades (35 + 4 novas) e 21 relacionamentos novos, em 6 domínios. Em verde, o que mudou na construção do banco.<BR/>"
                 "Sem elipses de atributo — elas estão nos diagramas 1 a 6.")
s = destaca_no(s, "HIST", "M21", texto="HISTÓRICO\n(derivado)", tracejado=True)
s = destaca_no(s, "ANAM", "M19")
def vrel(i, t, m): return rel(i, t, m)
blocos = {
 "cluster_1": ent("CONFIG", "CONFIGURAÇÃO\nDA UNIDADE", "M1") + vrel("V1", "configura", "M1") + vrel("V2", "pode agendar", "M2") + vrel("V3", "é", "M3"),
 "cluster_2": vrel("V4", "pertence a", "M4") + vrel("V5", "renova", "M5") + vrel("V6", "refere-se a", "M5") + vrel("V7", "debita", "M7"),
 "cluster_3": ent("LISTA", "LISTA DE\nESPERA", "M10") + vrel("V8", "aguarda", "M10") + vrel("V9", "para", "M10") +
              vrel("V10", "vale para", "M11") + vrel("V11", "vale para", "M11") + vrel("V12", "sobre", "M12") + vrel("V13", "escreve", "M12"),
 "cluster_4": ent("AVFISIO", "AVALIAÇÃO DE\nFISIOTERAPIA", "M14") + vrel("V14", "corrige", "M16") + vrel("V15", "realizada em", "M17"),
 "cluster_5": vrel("V16", "atendido em", "M13") + vrel("V17", "registrada em", "M19"),
 "cluster_6": ent("ACESSO", "ACESSO A DADO\nSENSÍVEL", "M23") + vrel("V18", "consulta", "M23") + vrel("V19", "sobre", "M23") +
              vrel("V20", "enviado por", "M20") + vrel("V21", "gera", "M24"),
}
for cl, bloco in blocos.items():
    i = s.index(f"subgraph {cl} {{")
    j = s.index("\n  }", i)
    s = s[:j] + "\n" + bloco.rstrip("\n") + s[j:]
pares = [("UNIDADE","V1","CONFIG",False), ("ATLETA","V2","SERVICO",False), ("USUARIO","V3","PROF",False),
         ("UNIDADE","V4","PLANO",False), ("ATLETA","V5","RENOVACAO",False), ("SERVICO","V6","RENOVACAO",False),
         ("AGEND","V7","LANC",True), ("ATLETA","V8","LISTA",False), ("SERVICO","V9","LISTA",False),
         ("UNIDADE","V10","BLOQUEIO",False), ("SERVICO","V11","BLOQUEIO",False), ("ATLETA","V12","RELAT",False),
         ("PROF","V13","RELAT",True), ("AVAL","V14","AVAL",False), ("UNIDADE","V15","AVAL",False),
         ("AGEND","V16","ATEND",True), ("AVAL","V17","ANAM",False), ("USUARIO","V18","ACESSO",True),
         ("ATLETA","V19","ACESSO",True), ("USUARIO","V20","ARQUIVO",False), ("EMISSAO","V21","ARQUIVO",False)]
arestas = "".join(lig(a, r, validar=v) + lig(r, b, validar=v) for a, r, b, v in pares)
arestas += f'  SP1 -- AVFISIO [style=dashed, color="{V2_COR}", penwidth=1.6];\n'
s = recolore_aresta(s, "R34 -- HIST")
s = antes_do_fim(s, arestas)
gravar("00-visao-geral.dot", s)

# ================================================================ Notação
legenda = f"""graph "notacao" {{
  graph [rankdir=LR, bgcolor="#FAFAF8", fontname="Helvetica", fontsize=20, pad=0.6, nodesep=0.35, ranksep=0.45,
         label=<<B>Notação — Peter Chen</B><BR/><FONT POINT-SIZE="12" COLOR="#6A6A6A">Convenção usada nos diagramas 0 a 6. Versão 2 (16/10/2026): acrescenta o verde para o que mudou na construção do banco.</FONT><BR/> >,
         labelloc=t, fontcolor="#2B2B2B"];
  node [fontname="Helvetica", fontsize=11];
  edge [fontname="Helvetica", fontsize=9, color="#5A5A5A", penwidth=1.1, fontcolor="#444444"];
  subgraph cluster_f {{ label="FORMAS"; fontsize=12; fontcolor="#7A7260"; style="rounded,dashed"; color="#C9C2B0"; margin=16;
    f1 [shape=box, style="filled,rounded", fillcolor="#EFEBE0", color="#8A7F66", penwidth=1.7, label="Entidade"];
    f2 [shape=box, style="filled,rounded", fillcolor="#E4E0F5", color="#6B5FA8", penwidth=1.7, label="Entidade\nfraca", peripheries=2];
    f3 [shape=diamond, style=filled, fillcolor="#FBEFD3", color="#B9963F", penwidth=1.3, label="relação", fontsize=10];
    f4 [shape=diamond, style=filled, fillcolor="#FBEFD3", color="#B9963F", penwidth=1.3, label="relação\nidentificadora", fontsize=10, peripheries=2];
    f5 [shape=ellipse, color="#9A9A9A", fontsize=10, label="atributo"];
    f6 [shape=ellipse, color="#9A9A9A", fontsize=10, label=<<U>chave</U>>];
    f7 [shape=ellipse, color="#9A9A9A", style=dashed, fontsize=10, label="derivado"];
    f8 [shape=box, style="filled,rounded,dashed", fillcolor="#EFEBE0", color="{V2_COR}", penwidth=2.2, label={tag("entidade derivada\n(view)", "M#")}];
    f9 [shape=triangle, color="#B9963F", label="d", fontsize=9, width=0.52, height=0.44];
    f1 -- f2 -- f3 -- f4 -- f5 -- f6 -- f7 -- f8 -- f9 [style=invis]; }}
  subgraph cluster_c {{ label="CORES"; fontsize=12; fontcolor="#7A7260"; style="rounded,dashed"; color="#C9C2B0"; margin=16;
    c1 [shape=box, style="filled,rounded", fillcolor="#EFEBE0", color="#8A7F66", penwidth=1.7, label="já existe\nno banco"];
    c2 [shape=box, style="filled,rounded", fillcolor="#E4E0F5", color="#6B5FA8", penwidth=1.7, label="proposta de\nnormalização"];
    c3 [shape=box, style="filled,rounded", fillcolor="#F3F3F1", color="#AFAFAF", penwidth=1.7, label="legado\n(a descontinuar)", fontcolor="#7A7A7A"];
    c4 [shape=box, style="filled,rounded", fillcolor="{V2_FILL}", color="{V2_COR}", penwidth=2.2, label={tag("nova na v2", "M#")}];
    c5 [shape=box, style="filled,rounded", fillcolor="#E4E0F5", color="{V2_COR}", penwidth=2.2, label={tag("existente que\nmudou na v2", "M#")}];
    c1 -- c2 -- c3 -- c4 -- c5 [style=invis]; }}
  subgraph cluster_k {{ label="COMO LER A CARDINALIDADE  (par mín,máx — fica JUNTO da entidade que ele descreve)"; fontsize=12; fontcolor="#7A7260"; style="rounded,dashed"; color="#C9C2B0"; margin=16;
    k1 [shape=box, style="filled,rounded", fillcolor="#EFEBE0", color="#8A7F66", penwidth=1.7, label="ATLETA", margin="0.18,0.10"];
    k2 [shape=diamond, style=filled, fillcolor="#FBEFD3", color="#B9963F", penwidth=1.3, label="reserva", fontsize=10];
    k3 [shape=box, style="filled,rounded", fillcolor="#EFEBE0", color="#8A7F66", penwidth=1.7, label="AGENDAMENTO", margin="0.18,0.10"];
    k4 [shape=plaintext, fontsize=10, fontcolor="#555555", label="um atleta reserva de 0 a N agendamentos;\num agendamento pertence a exatamente 1 atleta.\nCardinalidade em verde = mudou na v2."];
    k1 -- k2 [taillabel="(0,N)", labeldistance=2.6, labelangle=12]; k2 -- k3 [taillabel="(1,1)", labeldistance=2.6, labelangle=12]; k3 -- k4 [style=invis]; }}
  subgraph cluster_l {{ label="LINHAS"; fontsize=12; fontcolor="#7A7260"; style="rounded,dashed"; color="#C9C2B0"; margin=16;
    l1 [shape=plaintext, label="confirmado no banco"]; l2 [shape=plaintext, label="confirmado no banco"];
    l3 [shape=plaintext, label="A VALIDAR"]; l4 [shape=plaintext, label="A VALIDAR"];
    l5 [shape=plaintext, label="mudou na v2", fontcolor="{V2_COR}"]; l6 [shape=plaintext, label="mudou na v2", fontcolor="{V2_COR}"];
    l7 [shape=plaintext, label="mudou na v2, a validar", fontcolor="{V2_COR}"]; l8 [shape=plaintext, label="mudou na v2, a validar", fontcolor="{V2_COR}"];
    l1 -- l2; l3 -- l4 [style=dashed, color="#B9963F"]; l5 -- l6 [color="{V2_COR}", penwidth=1.6]; l7 -- l8 [color="{V2_COR}", penwidth=1.6, style=dashed]; }}
}}
"""
gravar("notacao.dot", legenda)

# ================================================================ render
ordem = ["notacao", "00-visao-geral", "01-cadastro", "02-comercial", "03-agenda", "04-avaliacao", "05-atendimento", "06-conformidade"]
for n in ordem:
    r = subprocess.run(["dot", "-Tpdf", os.path.join(OUT_DOT, n + ".dot"), "-o", os.path.join(OUT_PDF, n + ".pdf")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("ERRO", n, r.stderr); sys.exit(1)
    if r.stderr.strip():
        print("aviso", n, r.stderr.strip()[:300])
print("ok")
