"""Contrato de dados dos relatórios v2: leitura, normalização e validação.

Um arquivo de contrato (JSON) tem tudo o que um relatório precisa e nada além disso:

    {
      "versao": 1,
      "modalidade": "PKZ" | "ONE_TO_ONE",
      "tipo_relatorio": "semanal" | "mensal" | "anual",
      "periodo": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD"},
      "aluno": {"id", "nome", "data_nascimento", "idade", "categoria", "modalidade", "clube", "turno"},
      "sessoes":    [{"data", "hora_inicio", "status"}],            # presenças, faltas, cancelamentos, agendamentos
      "avaliacoes": [{"avaliacao_id", "data_avaliacao", "teste", "teste_nome", "lado",
                      "unidade_medida", "maior_melhor", "confirmado", "valor"}],
      "treinos":    [{"data", "tipo_treino", "intensidade", "objetivos", "desempenho", "observacoes"}],
      "grupo":      {"descricao", "avaliacoes": [{"aluno", "teste", "lado", "data_avaliacao", "valor",
                                                  "confirmado", "maior_melhor"}]},   # colegas, sem nomes
      "reavaliacao": {"ultima_avaliacao_em", "vence_em", "situacao"} | null,
      "observacoes": "texto livre" | null,
      "origem": {"fonte", "gerado_em", ...}
    }

Sessões, avaliações e treinos podem trazer registros de antes do período: eles servem de histórico
(comparação com a medição anterior, com o período anterior). Os indicadores do período usam só o
que está dentro dele.
"""
import json
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

VERSAO = 1
MODALIDADES = {"PKZ": "PKZ", "ONE_TO_ONE": "ONE_TO_ONE", "ONE TO ONE": "ONE_TO_ONE", "ONETOONE": "ONE_TO_ONE"}
TIPOS = ("semanal", "mensal", "anual")
STATUS = ("presente", "falta", "cancelado", "agendado")
SINONIMOS_STATUS = {"aguardando_confirmacao": "agendado", "ausente": "falta", "presenca": "presente",
                    "cancelada": "cancelado", "agendada": "agendado"}
CAMPOS_TREINO = ("tipo_treino", "intensidade", "objetivos", "desempenho", "observacoes")
# Textos de demonstração que nunca podem aparecer como dado real.
MARCAS_DE_DEMONSTRACAO = ("dado ficticio de demonstracao", "exemplo sintetico", "lorem ipsum")


class ContratoInvalido(Exception):
    """O contrato tem erros que impedem gerar o relatório."""

    def __init__(self, erros, avisos=()):
        self.erros, self.avisos = list(erros), list(avisos)
        super().__init__("\n".join(self.erros))


# ---------------------------------------------------------------- utilidades
def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")


def chave_nome(texto):
    """Nome normalizado para casar registros de fontes diferentes (sem acento, minúsculo, espaços simples)."""
    return " ".join(sem_acento(texto).lower().split())


def ler_data(valor):
    """Aceita AAAA-MM-DD (com ou sem hora) e DD/MM/AAAA. Devolve None se não for uma data válida."""
    if valor in (None, ""):
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    return None


def ler_numero(valor):
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def ler_booleano(valor):
    if isinstance(valor, bool) or valor is None:
        return valor
    texto = sem_acento(valor).strip().lower()
    if texto in ("true", "sim", "s", "1", "verdadeiro", "yes"):
        return True
    if texto in ("false", "nao", "n", "0", "falso", "no"):
        return False
    if texto in ("", "null", "none"):
        return None
    return "invalido"


def texto_real(valor):
    """O texto como veio, ou None se estiver vazio ou for marca de demonstração."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto in ("—", "-", "null", "None"):
        return None
    if any(m in chave_nome(texto) for m in MARCAS_DE_DEMONSTRACAO):
        return None
    return texto


def idade_em(nascimento, referencia):
    return referencia.year - nascimento.year - ((referencia.month, referencia.day) < (nascimento.month, nascimento.day))


def periodo_padrao(tipo, referencia):
    """Período completo que contém a data: semana de segunda a domingo, mês ou ano civil."""
    if tipo == "semanal":
        inicio = referencia - timedelta(days=referencia.weekday())
        return inicio, inicio + timedelta(days=6)
    if tipo == "mensal":
        inicio = referencia.replace(day=1)
        proximo = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
        return inicio, proximo - timedelta(days=1)
    return date(referencia.year, 1, 1), date(referencia.year, 12, 31)


# ---------------------------------------------------------------- leitura
def carregar(caminho):
    caminho = Path(caminho)
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as erro:
        raise ContratoInvalido([f"{caminho.name}: JSON inválido na linha {erro.lineno}, coluna {erro.colno} ({erro.msg})."])


def salvar(contrato, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(contrato, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return caminho


def modelo_vazio(modalidade="PKZ", tipo="mensal"):
    """Esqueleto do contrato, sem nenhum dado, para preencher à mão."""
    return {
        "versao": VERSAO,
        "modalidade": modalidade,
        "tipo_relatorio": tipo,
        "periodo": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD"},
        "aluno": {"id": None, "nome": None, "data_nascimento": None, "idade": None, "categoria": None,
                  "modalidade": None, "clube": None, "turno": None, "foto": None, "foto_ilustrativa": False},
        "sessoes": [],
        "avaliacoes": [],
        "treinos": [],
        "grupo": {"descricao": None, "avaliacoes": []},
        "reavaliacao": None,
        "observacoes": None,
        "origem": {"fonte": "manual"},
    }


# ---------------------------------------------------------------- validação e normalização
def validar(bruto, hoje=None):
    """Confere o contrato e devolve (contrato normalizado, erros, avisos).

    Erros impedem o relatório (data inválida, status desconhecido, período incompleto…).
    Avisos não impedem, mas aparecem na saída do comando e no fim do relatório quando mudam a leitura
    (registros duplicados descartados, ano com dados só de parte dos meses…).
    """
    hoje = hoje or date.today()
    erros, avisos = [], []
    if not isinstance(bruto, dict):
        return None, ["O contrato precisa ser um objeto JSON."], []

    modalidade = MODALIDADES.get(str(bruto.get("modalidade") or "").strip().upper().replace("-", " "))
    if not modalidade:
        erros.append("modalidade: use PKZ ou ONE_TO_ONE.")
    tipo = str(bruto.get("tipo_relatorio") or "").strip().lower()
    if tipo not in TIPOS:
        erros.append("tipo_relatorio: use semanal, mensal ou anual.")

    periodo = bruto.get("periodo") or {}
    inicio, fim = ler_data(periodo.get("inicio")), ler_data(periodo.get("fim"))
    if not inicio or not fim:
        erros.append("periodo: informe inicio e fim no formato AAAA-MM-DD.")
    elif inicio > fim:
        erros.append("periodo: a data inicial é depois da final.")
    elif tipo in TIPOS:
        esperado = periodo_padrao(tipo, inicio)
        if (inicio, fim) != esperado:
            nomes = {"semanal": "uma semana de segunda a domingo", "mensal": "um mês completo, do dia 1 ao último dia",
                     "anual": "um ano completo, de 01/01 a 31/12"}
            erros.append(f"periodo: o relatório {tipo} usa {nomes[tipo]} "
                         f"(para {inicio:%d/%m/%Y}: {esperado[0]:%d/%m/%Y} a {esperado[1]:%d/%m/%Y}).")
        if fim > hoje and inicio <= hoje:
            avisos.append(f"periodo: o período ainda não terminou (vai até {fim:%d/%m/%Y}); o relatório mostra o que existe até hoje.")
        elif inicio > hoje:
            erros.append("periodo: o período ainda não começou.")

    aluno_bruto = bruto.get("aluno") or {}
    nome = texto_real(aluno_bruto.get("nome"))
    if not nome:
        erros.append("aluno.nome: obrigatório.")
    nascimento = ler_data(aluno_bruto.get("data_nascimento"))
    if aluno_bruto.get("data_nascimento") and not nascimento:
        erros.append("aluno.data_nascimento: data inválida (use AAAA-MM-DD ou DD/MM/AAAA).")
    idade = aluno_bruto.get("idade")
    if idade is not None:
        try:
            idade = int(idade)
        except (TypeError, ValueError):
            erros.append("aluno.idade: precisa ser um número inteiro.")
            idade = None
    if nascimento and fim:
        calculada = idade_em(nascimento, min(fim, hoje))
        if idade is not None and abs(calculada - idade) > 1:
            avisos.append(f"aluno: a idade informada ({idade}) não bate com a data de nascimento ({calculada}); vale a data de nascimento.")
        idade = calculada
    aluno = {"id": aluno_bruto.get("id"), "nome": nome, "data_nascimento": nascimento.isoformat() if nascimento else None,
             "idade": idade}
    for campo in ("categoria", "modalidade", "clube", "turno"):
        aluno[campo] = texto_real(aluno_bruto.get(campo))
    # Foto do cartão (opcional): caminho de um JPG/PNG nesta máquina. Ilustrativa = não é do aluno (ex.: gerada por IA).
    foto = texto_real(aluno_bruto.get("foto"))
    if foto and not Path(foto).is_file():
        avisos.append(f"aluno.foto: arquivo não encontrado ({foto}); o cartão sai sem foto.")
        foto = None
    aluno["foto"] = foto
    aluno["foto_ilustrativa"] = bool(aluno_bruto.get("foto_ilustrativa")) if foto else False

    # -- sessões (presenças, faltas, cancelamentos e agendamentos)
    sessoes, vistos = [], set()
    for i, s in enumerate(bruto.get("sessoes") or [], start=1):
        d = ler_data(s.get("data"))
        status = SINONIMOS_STATUS.get(chave_nome(s.get("status")).replace(" ", "_"), chave_nome(s.get("status")).replace(" ", "_"))
        if not d:
            erros.append(f"sessoes[{i}]: data inválida ({s.get('data')!r}).")
            continue
        if status not in STATUS:
            erros.append(f"sessoes[{i}]: status desconhecido ({s.get('status')!r}); use presente, falta, cancelado ou agendado.")
            continue
        hora = str(s.get("hora_inicio") or "")[:5] or None
        chave = (d, hora, s.get("id") or s.get("agendamento_id"))
        if chave in vistos and chave[2] is None:
            avisos.append(f"sessoes[{i}]: registro repetido em {d:%d/%m/%Y}{' ' + hora if hora else ''}; foi contado uma vez só.")
            continue
        vistos.add(chave)
        if status == "presente" and d > hoje:
            erros.append(f"sessoes[{i}]: presença registrada numa data futura ({d:%d/%m/%Y}).")
            continue
        sessoes.append({"data": d.isoformat(), "hora_inicio": hora, "status": status})
    sessoes.sort(key=lambda s: (s["data"], s["hora_inicio"] or ""))
    pendentes = [s for s in sessoes if s["status"] == "agendado" and ler_data(s["data"]) < hoje]
    if pendentes:
        avisos.append(f"sessoes: {len(pendentes)} {'sessão passada continua' if len(pendentes) == 1 else 'sessões passadas continuam'} "
                      "como agendada, sem presença ou falta registrada; não entram na frequência.")

    # -- avaliações físicas
    avaliacoes, vistos, unidades = [], set(), {}
    for i, a in enumerate(bruto.get("avaliacoes") or [], start=1):
        d = ler_data(a.get("data_avaliacao"))
        teste = texto_real(a.get("teste"))
        if not d or not teste:
            erros.append(f"avaliacoes[{i}]: data_avaliacao e teste são obrigatórios.")
            continue
        valor = ler_numero(a.get("valor"))
        if a.get("valor") not in (None, "") and valor is None:
            erros.append(f"avaliacoes[{i}]: valor não numérico ({a.get('valor')!r}).")
            continue
        confirmado = ler_booleano(a.get("confirmado"))
        maior_melhor = ler_booleano(a.get("maior_melhor"))
        if confirmado == "invalido" or maior_melhor == "invalido":
            erros.append(f"avaliacoes[{i}]: confirmado e maior_melhor aceitam verdadeiro, falso ou vazio.")
            continue
        lado = (chave_nome(a.get("lado")) or None)
        lado = {"direito": "dir", "direita": "dir", "esquerdo": "esq", "esquerda": "esq"}.get(lado, lado)
        unidade = texto_real(a.get("unidade_medida")) or ""
        if unidades.setdefault(teste, unidade) != unidade:
            erros.append(f"avaliacoes[{i}]: o teste {teste} aparece com unidades diferentes ({unidades[teste]!r} e {unidade!r}).")
            continue
        chave = (a.get("avaliacao_id") or d, teste, lado)
        if chave in vistos:
            avisos.append(f"avaliacoes[{i}]: {teste} repetido na mesma avaliação de {d:%d/%m/%Y}; foi considerado uma vez só.")
            continue
        vistos.add(chave)
        if d > hoje:
            erros.append(f"avaliacoes[{i}]: avaliação numa data futura ({d:%d/%m/%Y}).")
            continue
        avaliacoes.append({"avaliacao_id": a.get("avaliacao_id") or f"aval-{d.isoformat()}", "data_avaliacao": d.isoformat(),
                           "teste": teste, "teste_nome": texto_real(a.get("teste_nome")) or teste, "lado": lado,
                           "unidade_medida": unidade, "maior_melhor": maior_melhor,
                           "confirmado": confirmado is True, "valor": valor})
    avaliacoes.sort(key=lambda a: (a["data_avaliacao"], a["teste"], a["lado"] or ""))

    # -- treinos registrados pelo professor
    treinos = []
    for i, t in enumerate(bruto.get("treinos") or [], start=1):
        d = ler_data(t.get("data"))
        if not d:
            erros.append(f"treinos[{i}]: data inválida ({t.get('data')!r}).")
            continue
        if d > hoje:
            erros.append(f"treinos[{i}]: relatório de treino numa data futura ({d:%d/%m/%Y}).")
            continue
        treinos.append({"data": d.isoformat(), **{c: texto_real(t.get(c)) for c in CAMPOS_TREINO}})
    treinos.sort(key=lambda t: t["data"])

    # -- colegas (sem nome) para a posição no grupo
    grupo_bruto = bruto.get("grupo") or {}
    grupo = []
    for a in grupo_bruto.get("avaliacoes") or []:
        d, v = ler_data(a.get("data_avaliacao")), ler_numero(a.get("valor"))
        if d and v is not None and a.get("teste"):
            grupo.append({"aluno": str(a.get("aluno") or ""), "teste": a["teste"], "lado": a.get("lado") or None,
                          "data_avaliacao": d.isoformat(), "valor": v, "confirmado": ler_booleano(a.get("confirmado")) is True,
                          "maior_melhor": ler_booleano(a.get("maior_melhor"))})

    reav = bruto.get("reavaliacao") or None
    if reav:
        reav = {"ultima_avaliacao_em": (ler_data(reav.get("ultima_avaliacao_em")) or "") and ler_data(reav.get("ultima_avaliacao_em")).isoformat(),
                "vence_em": (ler_data(reav.get("vence_em")) or "") and ler_data(reav.get("vence_em")).isoformat(),
                "situacao": texto_real(reav.get("situacao"))}
        if not reav["vence_em"]:
            reav = None

    contrato = {
        "versao": VERSAO, "modalidade": modalidade, "tipo_relatorio": tipo,
        "periodo": {"inicio": inicio.isoformat() if inicio else None, "fim": fim.isoformat() if fim else None},
        "aluno": aluno, "sessoes": sessoes, "avaliacoes": avaliacoes, "treinos": treinos,
        "grupo": {"descricao": texto_real(grupo_bruto.get("descricao")), "avaliacoes": grupo},
        "reavaliacao": reav, "observacoes": texto_real(bruto.get("observacoes")), "origem": bruto.get("origem") or {},
        "avisos": [],
    }

    # -- há o que mostrar no período?
    if not erros and inicio and fim:
        no_periodo = lambda lista, campo: [x for x in lista if inicio <= ler_data(x[campo]) <= fim]
        # No One to One as avaliações físicas só alimentam o cartão do atleta: o relatório precisa de chamada ou treino.
        conta_avaliacao = modalidade != "ONE_TO_ONE" and no_periodo(avaliacoes, "data_avaliacao")
        if not (no_periodo(sessoes, "data") or conta_avaliacao or no_periodo(treinos, "data")):
            erros.append(f"Sem nenhum registro de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}: não há relatório a gerar para este período.")
        if tipo == "anual":
            meses = sorted({ler_data(x["data"]).month for x in no_periodo(sessoes, "data")}
                           | {ler_data(x["data"]).month for x in no_periodo(treinos, "data")}
                           | {ler_data(x["data_avaliacao"]).month for x in no_periodo(avaliacoes, "data_avaliacao")})
            if meses and len(meses) < 12:
                contrato["avisos"].append("ano_incompleto")
                avisos.append(f"periodo: há registros em {len(meses)} dos 12 meses; o relatório anual não trata o ano como completo.")
    return contrato, erros, avisos


def validar_ou_falhar(bruto, hoje=None):
    contrato, erros, avisos = validar(bruto, hoje)
    if erros:
        raise ContratoInvalido(erros, avisos)
    return contrato, avisos
