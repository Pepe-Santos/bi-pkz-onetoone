import argparse
import os
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from dotenv import load_dotenv

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether,
)

# Estrutura do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "backend" / ".env"
API_DIR = BASE_DIR / "exemplos" / "api"
SAIDA_DIR = BASE_DIR / "gerador_pkz" / "relatorios"

load_dotenv(ENV_PATH)


def registrar_fontes():
    fonte_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    fonte_normal = fonte_dir / "DejaVuSans.ttf"
    fonte_negrito = fonte_dir / "DejaVuSans-Bold.ttf"

    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", str(fonte_normal)))
    if "DejaVu-Bold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(fonte_negrito)))


def normalizar(texto):
    texto = str(texto or "").lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def formatar_data(valor):
    if not valor:
        return "—"
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def formatar_valor(valor, unidade=""):
    if valor is None:
        return "—"

    if isinstance(valor, str):
        valor = valor.strip()

        if valor in ("â€”", "â€“", ""):
            return "—"

    unidades_exibicao = {
        "desequilibrios": "desequilíbrios"
    }

    unidade_exibicao = unidades_exibicao.get(unidade, unidade)

    if isinstance(valor, (int, float)):
        numero = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{numero} {unidade_exibicao or ''}".strip()

    return f"{valor} {unidade_exibicao or ''}".strip()


def formatar_percentual(valor):
    if valor is None:
        return "—"
    return f"{valor:+.1f}%".replace(".", ",")


def menor_e_melhor(maior_melhor):
    return maior_melhor is False


def data_avaliacao(registro):
    try:
        return date.fromisoformat(str(registro.get("data_avaliacao"))[:10])
    except (TypeError, ValueError):
        return None


def lado_normalizado(registro):
    lado = normalizar(registro.get("lado")).strip()
    return lado if lado in ("dir", "esq") else None


def chave_teste(registro):
    return registro.get("teste") or "outro", lado_normalizado(registro)


def nome_com_lado(registro):
    nome = registro.get("teste_nome") or registro.get("teste") or "—"
    lado = lado_normalizado(registro)
    if lado:
        nome += f" ({lado})"
    return nome


def montar_comparacoes(evolucoes_ate_fim):
    grupos = defaultdict(list)
    for registro in evolucoes_ate_fim:
        grupos[chave_teste(registro)].append(registro)

    resultado = []
    for registros in grupos.values():
        registros.sort(key=lambda item: data_avaliacao(item) or date.min)
        atual = registros[-1]
        anterior = registros[-2] if len(registros) > 1 else None

        valor_atual = atual.get("valor")
        valor_anterior = anterior.get("valor") if anterior else None
        maior_melhor = atual.get("maior_melhor")
        # variação % calculada sempre que houver valor anterior e atual,
        # inclusive quando o teste ainda está em validação
        variacao_pct = None
        if anterior is not None and valor_atual is not None and valor_anterior is not None:
            if valor_anterior != 0:
                variacao_pct = ((valor_atual - valor_anterior) / abs(valor_anterior)) * 100
            elif valor_atual == 0:
                variacao_pct = 0.0

        if atual.get("confirmado") is False:
            situacao = "em_validacao"
        elif anterior is None:
            situacao = "sem_comparacao"
        elif variacao_pct is None or maior_melhor is None:
            situacao = "sem_classificacao"
        elif abs(variacao_pct) < 2:
            situacao = "estavel"
        elif (variacao_pct > 0) == maior_melhor:
            situacao = "melhorou"
        else:
            situacao = "piorou"

        resultado.append({
            "teste": atual.get("teste"),
            "teste_nome": atual.get("teste_nome"),
            "lado": atual.get("lado"),
            "unidade_medida": atual.get("unidade_medida", ""),
            "maior_melhor": maior_melhor,
            "confirmado": atual.get("confirmado"),
            "valor_anterior": valor_anterior,
            "valor_atual": valor_atual,
            "variacao_pct": variacao_pct,
            "situacao": situacao,
        })

    return sorted(resultado, key=lambda item: (
        str(item.get("teste") or ""),
        str(item.get("lado") or "")
    ))


def formatar_situacao(valor):
    situacoes = {
        "sem_classificacao": "Sem classificação",
        "sem_comparacao": "Sem comparação",
        "em_validacao": "Em validação",
        "melhorou": "Melhorou",
        "piorou": "Piorou",
        "estavel": "Estável",
    }
    chave = normalizar(valor).replace(" ", "_")
    return situacoes.get(chave, str(valor or "—").replace("_", " ").capitalize())


def periodo_datas(periodo, referencia):
    if periodo == "semanal":
        inicio = referencia - timedelta(days=referencia.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == "mensal":
        inicio = referencia.replace(day=1)
        if referencia.month == 12:
            proximo = date(referencia.year + 1, 1, 1)
        else:
            proximo = date(referencia.year, referencia.month + 1, 1)
        fim = proximo - timedelta(days=1)
    elif periodo == "anual":
        inicio = date(referencia.year, 1, 1)
        fim = date(referencia.year, 12, 31)
    else:
        raise ValueError("Período inválido. Use semanal, mensal ou anual.")
    return inicio, fim


def titulo_periodo(periodo, inicio, fim):
    if periodo == "semanal":
        return f"Relatório semanal — {inicio:%d/%m} a {fim:%d/%m/%Y}"
    if periodo == "mensal":
        return f"Relatório mensal — {inicio:%m/%Y}"
    return f"Relatório anual — {inicio:%Y}"


def carregar_json(nome):
    caminho = API_DIR / nome
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    import json
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def buscar_api(view, filtros=None, order=None):
    base_url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_SECRET_KEY")
    if not base_url or not chave:
        raise RuntimeError(
            f"Credenciais ausentes. Confira {ENV_PATH} e preencha SUPABASE_URL e SUPABASE_SECRET_KEY."
        )
    headers = {
        "apikey": chave,
        "Authorization": f"Bearer {chave}",
        "Accept-Profile": "api",
    }
    params = dict(filtros or {})
    if order:
        params["order"] = order
    url = base_url.rstrip("/") + f"/rest/v1/{view}"
    resposta = requests.get(url, headers=headers, params=params, timeout=30)
    if not resposta.ok:
        raise RuntimeError(
            f"Erro ao consultar a view '{view}' (HTTP {resposta.status_code}): {resposta.text[:600]}"
        )
    dados = resposta.json()
    if not isinstance(dados, list):
        raise RuntimeError(f"A view '{view}' não retornou uma lista de registros.")
    return dados


def buscar_dados_atleta(atleta_id):
    filtros_atleta = {"unidade": "eq.PKZ", "select": "atleta_id,unidade,nome,idade,categoria,ativo,total_avaliacoes,ultima_avaliacao_em"}
    if atleta_id:
        filtros_atleta["atleta_id"] = f"eq.{atleta_id}"
    else:
        filtros_atleta["limit"] = 1
    atletas = buscar_api("atleta", filtros_atleta)
    if not atletas:
        raise ValueError(f"Atleta PKZ não encontrado: {atleta_id or '(primeiro atleta)'}")
    atleta = atletas[0]
    if atleta.get("unidade") != "PKZ":
        raise ValueError("O atleta informado não pertence à unidade PKZ.")
    aid = atleta["atleta_id"]
    comparacoes = buscar_api("comparacao", {"atleta_id": f"eq.{aid}"})
    evolucoes = buscar_api(
        "evolucao", {"atleta_id": f"eq.{aid}"}, order="data_avaliacao.asc"
    )
    presencas = buscar_api("presenca", {"atleta_id": f"eq.{aid}"}, order="data.asc")
    return atleta, comparacoes, evolucoes, presencas


def criar_grafico(registros, nome_teste):
    confirmados = [
        item for item in registros
        if item.get("confirmado") is True and item.get("valor") is not None
    ]
    confirmados.sort(key=lambda item: item.get("data_avaliacao") or "")
    if not confirmados:
        return None
    datas = [formatar_data(item.get("data_avaliacao")) for item in confirmados]
    valores = [item["valor"] for item in confirmados]
    unidade = confirmados[0].get("unidade_medida", "")
    figura, eixo = plt.subplots(figsize=(7, 3))
    eixo.plot(datas, valores, marker="o", linewidth=2)
    eixo.set_title(nome_teste, pad=10)
    eixo.set_ylabel(f"Resultado ({unidade})" if unidade else "Resultado")
    eixo.set_xlabel("Data da avaliação")
    eixo.grid(True, linestyle="--", alpha=0.4)
    eixo.tick_params(axis="x", rotation=20)
    figura.tight_layout()
    imagem = BytesIO()
    figura.savefig(imagem, format="png", dpi=150, bbox_inches="tight")
    plt.close(figura)
    imagem.seek(0)
    return imagem


def calcular_frequencia(presencas, inicio, fim):
    no_periodo = []
    for item in presencas:
        try:
            data_item = date.fromisoformat(str(item.get("data"))[:10])
        except (TypeError, ValueError):
            continue
        if inicio <= data_item <= fim:
            no_periodo.append(item)
    contagem = defaultdict(int)
    for item in no_periodo:
        status = normalizar(item.get("status", ""))
        contagem[status] += 1
    presentes = contagem["presente"]
    faltas = contagem["falta"]
    cancelados = contagem["cancelado"]
    agendados = contagem["agendado"]
    base_frequencia = presentes + faltas
    percentual = (presentes / base_frequencia * 100) if base_frequencia else None
    return no_periodo, presentes, faltas, cancelados, agendados, percentual


def criar_tabela(dados, larguras, tamanho=8):
    # Quebra nomes longos na primeira coluna para evitar sobreposição
    # com as colunas de valores (por exemplo, nomes extensos de testes VO2).
    estilos_celula = getSampleStyleSheet()
    estilo_primeira_coluna = ParagraphStyle(
        name=f"CelulaTabelaPKZ{tamanho}",
        parent=estilos_celula["Normal"],
        fontName="DejaVu",
        fontSize=tamanho,
        leading=tamanho + 2,
        wordWrap="CJK",
    )

    dados_formatados = [list(linha) for linha in dados]
    for indice in range(1, len(dados_formatados)):
        valor = dados_formatados[indice][0]
        if not isinstance(valor, Paragraph):
            texto = str(valor).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            dados_formatados[indice][0] = Paragraph(texto, estilo_primeira_coluna)

    tabela = Table(dados_formatados, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B55")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), tamanho),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C8D8D1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F7F5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabela


def gerar_relatorio(atleta_id, periodo, referencia):
    inicio, fim = periodo_datas(periodo, referencia)
    atleta, comparacoes_api, evolucoes, presencas = buscar_dados_atleta(atleta_id)
    aid = atleta["atleta_id"]

    evolucoes_ate_fim = [
        registro for registro in evolucoes
        if data_avaliacao(registro) is not None and data_avaliacao(registro) <= fim
    ]
    evolucoes_periodo = [
        registro for registro in evolucoes_ate_fim
        if inicio <= data_avaliacao(registro) <= fim
    ]

    avaliacoes_ids = {
        registro.get("avaliacao_id")
        for registro in evolucoes_periodo
        if registro.get("avaliacao_id")
    }
    avaliacoes_ate_fim_ids = {
        registro.get("avaliacao_id")
        for registro in evolucoes_ate_fim
        if registro.get("avaliacao_id")
    }
    datas_ate_fim = [
        data_avaliacao(registro) for registro in evolucoes_ate_fim
        if data_avaliacao(registro) is not None
    ]
    atleta["total_avaliacoes"] = len(avaliacoes_ate_fim_ids)
    atleta["ultima_avaliacao_em"] = max(datas_ate_fim).isoformat() if datas_ate_fim else None
    comparacoes = montar_comparacoes(evolucoes_ate_fim)

    presencas_periodo, presentes, faltas, cancelados, agendados, percentual = calcular_frequencia(
        presencas, inicio, fim
    )
    if not evolucoes_periodo and not presencas_periodo:
        print(
            f"Nenhuma avaliação ou agendamento no período {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}. PDF não gerado."
        )
        return None

    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    destino = SAIDA_DIR / f"relatorio_pkz_{aid}_{periodo}_{referencia:%Y-%m-%d}.pdf"

    registrar_fontes()
    estilos = getSampleStyleSheet()
    for estilo in estilos.byName.values():
        estilo.fontName = "DejaVu"
    estilos.add(ParagraphStyle(name="TituloPKZ", parent=estilos["Title"], alignment=TA_CENTER,
                               textColor=colors.HexColor("#176B55"), fontSize=22, spaceAfter=8))
    estilos.add(ParagraphStyle(name="SubtituloPKZ", parent=estilos["Heading2"],
                               textColor=colors.HexColor("#176B55"), spaceBefore=12, spaceAfter=8))
    estilos.add(ParagraphStyle(name="AvisoPKZ", parent=estilos["Normal"], textColor=colors.HexColor("#555555"),
                               fontSize=9, leading=12))
    estilos.add(ParagraphStyle(name="NotaGraficoPKZ", parent=estilos["Normal"], alignment=TA_CENTER,
                               textColor=colors.HexColor("#176B55"), fontSize=9, leading=12,
                               spaceBefore=2, spaceAfter=8))

    documento = SimpleDocTemplate(str(destino), pagesize=A4, rightMargin=1.5 * cm,
                                  leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    conteudo = [
        Paragraph("PKZ — Relatório de Evolução", estilos["TituloPKZ"]),
        Paragraph(titulo_periodo(periodo, inicio, fim), estilos["Heading2"]),
        Paragraph("Relatório gerado automaticamente a partir dos dados de avaliação e frequência.", estilos["Normal"]),
        Spacer(1, 14),
        Paragraph("Identificação do atleta", estilos["SubtituloPKZ"]),
    ]

    identificacao = [
        ["Campo", "Informação"],
        ["Atleta", atleta.get("nome") or "Não informado"],
        ["Unidade", atleta.get("unidade") or "—"],
        ["Idade", str(atleta.get("idade") or "—")],
        ["Categoria", atleta.get("categoria") or "—"],
        ["Total de avaliações", str(atleta.get("total_avaliacoes", "—"))],
        ["Última avaliação", formatar_data(atleta.get("ultima_avaliacao_em"))],
    ]
    tabela_identificacao = Table(identificacao, colWidths=[5 * cm, 11 * cm])
    tabela_identificacao.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B55")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#E8F4EF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D8D1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    conteudo.extend([tabela_identificacao, Spacer(1, 12)])

    conteudo.append(Paragraph("No período", estilos["SubtituloPKZ"]))
    frequencia = [
        ["Indicador", "Quantidade"],
        ["Avaliações realizadas", str(len(avaliacoes_ids))],
        ["Presenças", str(presentes)],
        ["Faltas", str(faltas)],
        ["Cancelamentos", str(cancelados)],
        ["Agendamentos", str(agendados)],
        ["Frequência", f"{percentual:.1f}%".replace(".", ",") if percentual is not None else "Sem dados"],
    ]
    conteudo.extend([criar_tabela(frequencia, [8 * cm, 8 * cm]), Spacer(1, 12)])

    conteudo.append(Paragraph("Avaliação atual x anterior", estilos["SubtituloPKZ"]))
    linhas = [["Teste", "Anterior", "Atual", "Variação", "Situação"]]
    for item in comparacoes:
        unidade = item.get("unidade_medida", "")
        situacao = formatar_situacao(item.get("situacao"))
        nome_teste = nome_com_lado(item)

        linhas.append([
            nome_teste,
            formatar_valor(item.get("valor_anterior"), unidade),
            formatar_valor(item.get("valor_atual"), unidade),
            formatar_percentual(item.get("variacao_pct")),
            situacao,
        ])
    if len(linhas) == 1:
        linhas.append(["Sem comparações disponíveis", "—", "—", "—", "—"])
    conteudo.extend([criar_tabela(linhas, [4.1 * cm, 2.8 * cm, 2.8 * cm, 2.3 * cm, 3.4 * cm]), Spacer(1, 12)])

    conteudo.append(Paragraph("Evolução histórica por teste", estilos["SubtituloPKZ"]))
    grupos = defaultdict(list)
    for registro in evolucoes_ate_fim:
        grupos[chave_teste(registro)].append(registro)

    if not grupos:
        conteudo.append(Paragraph(
            "Nenhuma avaliação registrada até o final deste período.",
            estilos["AvisoPKZ"]
        ))

    for (codigo, lado), registros in sorted(grupos.items(), key=lambda g: (str(g[0][0]), str(g[0][1] or ""))):
        registros.sort(key=lambda item: data_avaliacao(item) or date.min)
        nome = nome_com_lado(registros[0])
        # direção do resultado: valor mais recente que tenha maior_melhor definido
        maior_melhor_grupo = next(
            (r.get("maior_melhor") for r in reversed(registros) if r.get("maior_melhor") is not None),
            None,
        )

        grafico = criar_grafico(registros, nome)
        if grafico:
            elementos = [Paragraph(nome, estilos["Heading3"]), Image(grafico, width=15 * cm, height=6.4 * cm)]
            if menor_e_melhor(maior_melhor_grupo):
                elementos.append(Paragraph("Menor = melhor resultado", estilos["NotaGraficoPKZ"]))
            elementos.append(Spacer(1, 8))
            conteudo.append(KeepTogether(elementos))
        else:
            bloco = [
                Paragraph(nome, estilos["Heading3"]),
                Paragraph("Gráfico disponível depois que a PKZ validar este teste.", estilos["AvisoPKZ"]),
            ]
            if menor_e_melhor(maior_melhor_grupo):
                bloco.append(Paragraph("Menor = melhor resultado", estilos["NotaGraficoPKZ"]))
            bloco.append(Spacer(1, 8))
            conteudo.append(KeepTogether(bloco))
    conteudo.extend([
        Spacer(1, 10),
        Paragraph("Os resultados em validação não são apresentados como resultados confirmados nos gráficos.", estilos["Italic"]),
    ])
    documento.build(conteudo)
    print(f"PDF gerado: {destino}")
    return destino




def carregar_dados_one_to_one(atleta_id, inicio, fim):
    filtros_atleta = {
        "unidade": "eq.ONE_TO_ONE",
        "atleta_id": f"eq.{atleta_id}",
        "select": "atleta_id,unidade,nome,idade,ativo"
    }

    atletas = buscar_api("atleta", filtros_atleta)

    if not atletas:
        raise ValueError(
            f"Atleta ONE_TO_ONE não encontrado: {atleta_id}"
        )

    atleta = atletas[0]

    presencas = buscar_api(
        "presenca",
        {
            "atleta_id": f"eq.{atleta_id}",
            "unidade": "eq.ONE_TO_ONE",
            "data": [
                f"gte.{inicio.isoformat()}",
                f"lte.{fim.isoformat()}"
            ],
            "select": "atleta_id,unidade,data,status"
        },
        order="data.asc"
    )

    treinos = buscar_api(
        "treino",
        {
            "atleta_id": f"eq.{atleta_id}",
            "unidade": "eq.ONE_TO_ONE",
            "data": [
                f"gte.{inicio.isoformat()}",
                f"lte.{fim.isoformat()}"
            ],
            "select": (
                "atleta_id,unidade,data,tipo_treino,"
                "intensidade,objetivos,desempenho"
            )
        },
        order="data.asc"
    )

    return atleta, presencas, treinos


def gerar_relatorio_one_to_one(atleta_id, periodo, referencia):
    inicio, fim = periodo_datas(periodo, referencia)

    atleta, presencas, treinos = carregar_dados_one_to_one(
        atleta_id, inicio, fim
    )

    if not presencas and not treinos:
        print(
            "Nenhum agendamento ou treino encontrado "
            "no período informado. PDF não gerado."
        )
        return None

    presentes = sum(
        1 for item in presencas
        if normalizar(item.get("status")) == "presente"
    )

    faltas = sum(
        1 for item in presencas
        if normalizar(item.get("status")) == "falta"
    )

    cancelados = sum(
        1 for item in presencas
        if normalizar(item.get("status")) == "cancelado"
    )

    agendados = sum(
        1 for item in presencas
        if normalizar(item.get("status")) in (
            "agendado", "aguardando_confirmacao"
        )
    )

    total_considerado = presentes + faltas

    percentual = (
        presentes / total_considerado * 100
        if total_considerado else 0
    )

    SAIDA_DIR.mkdir(parents=True, exist_ok=True)

    nome_arquivo = (
        f"relatorio_one_to_one_{periodo}_"
        f"{atleta_id}_{referencia.isoformat()}.pdf"
    )

    destino = SAIDA_DIR / nome_arquivo

    registrar_fontes()

    estilos = getSampleStyleSheet()

    for estilo in estilos.byName.values():
        estilo.fontName = "DejaVu"

    titulo = ParagraphStyle(
        "TituloOneToOne",
        parent=estilos["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=15
    )

    subtitulo = ParagraphStyle(
        "SubtituloOneToOne",
        parent=estilos["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=12,
        spaceAfter=8
    )

    texto_pdf = ParagraphStyle(
        "TextoOneToOne",
        parent=estilos["BodyText"],
        fontSize=9,
        leading=13
    )

    texto_tabela = ParagraphStyle(
        "TabelaOneToOne",
        parent=estilos["BodyText"],
        fontSize=8,
        leading=10
    )

    elementos = [
        Paragraph("RELATÓRIO ONE TO ONE", titulo),
        Paragraph(
            f"Aluno: {escape(str(atleta.get('nome') or 'Aluno'))}",
            texto_pdf
        ),
        Paragraph(f"Período: {periodo.capitalize()}", texto_pdf),
        Paragraph(
            f"Referência: {referencia.strftime('%d/%m/%Y')}",
            texto_pdf
        ),
        Paragraph(
            f"Intervalo: {inicio.strftime('%d/%m/%Y')} "
            f"até {fim.strftime('%d/%m/%Y')}",
            texto_pdf
        ),
        Spacer(1, 15),
        Paragraph("Resumo de presença", subtitulo)
    ]

    dados_presenca = [
        ["Indicador", "Quantidade"],
        ["Presenças", str(presentes)],
        ["Faltas", str(faltas)],
        ["Cancelamentos", str(cancelados)],
        ["Agendamentos", str(agendados)],
        ["Percentual de presença", f"{percentual:.2f}%"]
    ]

    tabela_presenca = Table(
        dados_presenca,
        colWidths=[9 * cm, 5 * cm]
    )

    tabela_presenca.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F6F8")),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    elementos.extend([
        tabela_presenca,
        Spacer(1, 12),
        Paragraph(
            "O percentual de presença considera apenas presenças "
            "e faltas. Cancelamentos e agendamentos não entram "
            "no cálculo.",
            texto_pdf
        ),
        Spacer(1, 15),
        Paragraph("Treinos realizados", subtitulo),
        Paragraph(
            f"Total de treinos no período: {len(treinos)}",
            texto_pdf
        ),
        Spacer(1, 12)
    ])

    treinos_ordenados = sorted(
        treinos,
        key=lambda item: str(item.get("data") or "")
    )

    treinos_exibidos = (
        treinos_ordenados[-10:]
        if periodo == "anual"
        else treinos_ordenados
    )

    dados_treinos = [[
        "Data", "Objetivos", "Tipo", "Intensidade", "Desempenho"
    ]]

    def valor_tabela(valor):
        if not valor:
            return "-"

        valor = str(valor)

        if "dado ficticio de demonstracao" in normalizar(valor):
            return "-"

        return escape(valor)

    for treino in treinos_exibidos:
        dados_treinos.append([
            Paragraph(formatar_data(treino.get("data")), texto_tabela),
            Paragraph(valor_tabela(treino.get("objetivos")), texto_tabela),
            Paragraph(valor_tabela(treino.get("tipo_treino")), texto_tabela),
            Paragraph(valor_tabela(treino.get("intensidade")), texto_tabela),
            Paragraph(valor_tabela(treino.get("desempenho")), texto_tabela)
        ])

    if not treinos_exibidos:
        dados_treinos.append([
            "-", Paragraph("Nenhum treino registrado.", texto_tabela),
            "-", "-", "-"
        ])

    tabela_treinos = Table(
        dados_treinos,
        colWidths=[
            2.1 * cm, 3.8 * cm, 3.3 * cm, 2.5 * cm, 4.3 * cm
        ],
        repeatRows=1
    )

    tabela_treinos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F6F8")),
        ("PADDING", (0, 0), (-1, -1), 5)
    ]))

    elementos.append(tabela_treinos)

    if periodo == "anual" and len(treinos) > 10:
        elementos.extend([
            Spacer(1, 8),
            Paragraph(
                "Este relatório apresenta os 10 treinos mais recentes. "
                "O total acima considera todos os treinos do período.",
                texto_pdf
            )
        ])

    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    documento.build(elementos)

    print(f"PDF One to One gerado: {destino}")
    return destino


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de relatérios PKZ e One to One."
    )

    parser.add_argument(
        "atleta_id",
        help="ID do atleta na API do Supabase"
    )

    parser.add_argument(
        "--one-to-one",
        action="store_true"
    )

    parser.add_argument(
        "--periodo",
        choices=["semanal", "mensal", "anual"],
        default="mensal"
    )

    parser.add_argument(
        "--referencia",
        default=(date.today() - timedelta(days=1)).isoformat()
    )

    args = parser.parse_args()

    try:
        referencia = date.fromisoformat(args.referencia)
    except ValueError:
        parser.error("--referencia deve estar no formato YYYY-MM-DD")

    if args.one_to_one:
        gerar_relatorio_one_to_one(
            args.atleta_id,
            args.periodo,
            referencia
        )
    else:
        gerar_relatorio(args.atleta_id, args.periodo, referencia)


if __name__ == "__main__":
    main()
