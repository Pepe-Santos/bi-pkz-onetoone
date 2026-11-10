import argparse
import json
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
API_PAGE_SIZE = 1000

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

        if valor in ("—", "–", ""):
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
        variacao_abs = None
        variacao_pct = None
        if anterior is not None and valor_atual is not None and valor_anterior is not None:
            variacao_abs = valor_atual - valor_anterior
            if valor_anterior != 0:
                variacao_pct = (variacao_abs / valor_anterior) * 100

        if atual.get("confirmado") is not True:
            situacao = "em_validacao"
        elif anterior is None:
            situacao = "sem_comparacao"
        elif variacao_abs is None:
            situacao = "sem_classificacao"
        elif variacao_abs == 0 or (variacao_pct is not None and abs(variacao_pct) < 2):
            situacao = "estavel"
        elif maior_melhor not in (True, False):
            situacao = "sem_classificacao"
        elif (variacao_abs > 0) == maior_melhor:
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


def carregar_json(nome, diretorio=None, obrigatorio=True):
    caminho = Path(diretorio or API_DIR) / nome
    if not caminho.exists():
        if not obrigatorio:
            return []
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, list):
        raise ValueError(f"O arquivo {caminho} deve conter uma lista JSON de registros.")
    if not all(isinstance(registro, dict) for registro in dados):
        raise ValueError(f"Todos os registros em {caminho} devem ser objetos JSON.")
    return dados


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
    try:
        limite_solicitado = int(params["limit"])
    except (KeyError, TypeError, ValueError):
        limite_solicitado = None
    url = base_url.rstrip("/") + f"/rest/v1/{view}"
    dados_completos = []
    offset = 0
    pagina_anterior = None
    while True:
        headers_paginados = {
            **headers,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + API_PAGE_SIZE - 1}",
            "Prefer": "count=exact",
        }
        resposta = requests.get(url, headers=headers_paginados, params=params, timeout=30)
        if not resposta.ok:
            raise RuntimeError(
                f"Erro ao consultar a view '{view}' (HTTP {resposta.status_code}): {resposta.text[:600]}"
            )
        pagina = resposta.json()
        if not isinstance(pagina, list):
            raise RuntimeError(f"A view '{view}' não retornou uma lista de registros.")
        dados_completos.extend(pagina)
        if limite_solicitado is not None and len(dados_completos) >= limite_solicitado:
            break
        content_range = resposta.headers.get("Content-Range", "")
        faixa = content_range.split("/", 1)[0]
        if "-" in faixa:
            try:
                inicio_faixa = int(faixa.split("-", 1)[0])
            except ValueError:
                inicio_faixa = offset
            if inicio_faixa != offset:
                raise RuntimeError(
                    f"A view '{view}' não respeitou a paginação solicitada."
                )
        total = content_range.rsplit("/", 1)[-1]
        total_conhecido = total.isdigit()
        if total_conhecido and offset + len(pagina) >= int(total):
            break
        if not total_conhecido and len(pagina) < API_PAGE_SIZE:
            break
        if not pagina:
            break
        if pagina == pagina_anterior:
            raise RuntimeError(
                f"A view '{view}' repetiu uma página; os resultados não foram paginados com segurança."
            )
        pagina_anterior = pagina
        offset += len(pagina)
    return dados_completos


def buscar_dados_atleta(atleta_id, json_dir=None):
    if json_dir is not None:
        atletas = carregar_json("atleta.json", json_dir)
        evolucoes = carregar_json("evolucao.json", json_dir)
        presencas = carregar_json("presenca.json", json_dir, obrigatorio=False)
        candidatos = [
            atleta for atleta in atletas
            if atleta.get("unidade") == "PKZ"
            and (not atleta_id or atleta.get("atleta_id") == atleta_id)
        ]
        if not candidatos:
            raise ValueError(
                f"Atleta PKZ não encontrado no JSON: {atleta_id or '(primeiro atleta PKZ)'}"
            )
        atleta = candidatos[0]
        aid = atleta.get("atleta_id")
        evolucoes = [item for item in evolucoes if item.get("atleta_id") == aid]
        presencas = [item for item in presencas if item.get("atleta_id") == aid]
        return atleta, [], evolucoes, presencas

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
    # A consulta à view faz parte do contrato de integração PKZ. O PDF recalcula
    # as situações a partir de evolucao para aplicar período e confirmação localmente.
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


def criar_tabela(dados, larguras, tamanho=8, envolver_todas_colunas=False):
    # Quebra textos longos nas colunas solicitadas para evitar sobreposição.
    estilos_celula = getSampleStyleSheet()
    estilo_primeira_coluna = ParagraphStyle(
        name=f"CelulaTabelaPKZ{tamanho}",
        parent=estilos_celula["Normal"],
        fontName="DejaVu",
        fontSize=tamanho,
        leading=tamanho + 2,
    )

    dados_formatados = [list(linha) for linha in dados]
    for indice in range(1, len(dados_formatados)):
        colunas = range(len(dados_formatados[indice])) if envolver_todas_colunas else range(1)
        for coluna in colunas:
            valor = dados_formatados[indice][coluna]
            if not isinstance(valor, Paragraph):
                dados_formatados[indice][coluna] = Paragraph(
                    escape(str(valor)), estilo_primeira_coluna
                )

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


def gerar_relatorio(atleta_id, periodo, referencia, json_dir=None):
    inicio, fim = periodo_datas(periodo, referencia)
    # A consulta a comparacao é mantida; a tabela do PDF é recalculada com evolucoes filtradas.
    atleta, _comparacoes_api, evolucoes, presencas = buscar_dados_atleta(atleta_id, json_dir)
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
    conteudo.extend([
        criar_tabela(
            linhas,
            [4.1 * cm, 2.8 * cm, 2.8 * cm, 2.3 * cm, 3.4 * cm],
            envolver_todas_colunas=True,
        ),
        Spacer(1, 12),
    ])

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

    filtro_periodo = (
        f"(data.gte.{inicio.isoformat()},"
        f"data.lte.{fim.isoformat()})"
    )

    presencas = buscar_api(
        "presenca",
        {
            "atleta_id": f"eq.{atleta_id}",
            "unidade": "eq.ONE_TO_ONE",
            "and": filtro_periodo,
            "select": "atleta_id,unidade,data,status"
        },
        order="data.asc"
    )

    treinos = buscar_api(
        "treino",
        {
            "atleta_id": f"eq.{atleta_id}",
            "unidade": "eq.ONE_TO_ONE",
            "and": filtro_periodo,
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
            "no per\u00edodo informado. PDF n\u00e3o gerado."
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
        if total_considerado else None
    )

    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    destino = SAIDA_DIR / (
        f"relatorio_one_to_one_{periodo}_"
        f"{atleta_id}_{referencia.isoformat()}.pdf"
    )

    registrar_fontes()
    estilos = getSampleStyleSheet()

    for estilo in estilos.byName.values():
        estilo.fontName = "DejaVu"

    estilos.add(ParagraphStyle(
        name="TituloOneToOne",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#176B55"),
        fontName="DejaVu-Bold",
        fontSize=19,
        spaceAfter=5
    ))
    estilos.add(ParagraphStyle(
        name="SubtituloOneToOne",
        parent=estilos["Heading2"],
        textColor=colors.HexColor("#176B55"),
        fontName="DejaVu-Bold",
        spaceBefore=7,
        spaceAfter=5
    ))
    estilos.add(ParagraphStyle(
        name="AvisoOneToOne",
        parent=estilos["Normal"],
        textColor=colors.HexColor("#555555"),
        fontSize=9,
        leading=12
    ))
    estilos.add(ParagraphStyle(
        name="CelulaOneToOne",
        parent=estilos["Normal"],
        fontName="DejaVu",
        fontSize=8,
        leading=10
    ))

    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )

    conteudo = [
        Paragraph("ONE TO ONE \u2014 Relat\u00f3rio de Acompanhamento",
                  estilos["TituloOneToOne"]),
        Paragraph(
            titulo_periodo(periodo, inicio, fim),
            estilos["Heading2"]
        ),
        Paragraph(
            "Relat\u00f3rio gerado automaticamente a partir dos dados "
            "de frequ\u00eancia e treinamento.",
            estilos["Normal"]
        ),
        Spacer(1, 7),
        Paragraph("Identifica\u00e7\u00e3o do aluno",
                  estilos["SubtituloOneToOne"])
    ]

    identificacao = [
        ["Campo", "Informa\u00e7\u00e3o"],
        ["Aluno", escape(str(atleta.get("nome") or "N\u00e3o informado"))],
        ["Unidade", "ONE TO ONE"],
        ["Idade", str(atleta.get("idade") or "?")],
        ["Situa\u00e7\u00e3o", "Ativo" if atleta.get("ativo") else "N\u00e3o informado"],
        ["Per\u00edodo", f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"]
    ]

    conteudo.extend([
        criar_tabela(identificacao, [5 * cm, 11 * cm]),
        Spacer(1, 6),
        Paragraph("No per\u00edodo", estilos["SubtituloOneToOne"])
    ])

    frequencia = [
        ["Indicador", "Quantidade"],
        ["Treinos realizados", str(len(treinos))],
        ["Presen\u00e7as", str(presentes)],
        ["Faltas", str(faltas)],
        ["Cancelamentos", str(cancelados)],
        ["Agendamentos", str(agendados)],
        [
            "Frequ\u00eancia",
            f"{percentual:.1f}%".replace(".", ",")
            if percentual is not None else "Sem dados"
        ]
    ]

    conteudo.extend([
        criar_tabela(frequencia, [8 * cm, 8 * cm]),
        Spacer(1, 4),
        Paragraph(
            "O percentual de frequ\u00eancia considera apenas presen\u00e7as "
            "e faltas. Cancelamentos e agendamentos n\u00e3o entram "
            "no c\u00e1lculo.",
            estilos["AvisoOneToOne"]
        ),
        Spacer(1, 6),
        Paragraph("Hist\u00f3rico de treinos",
                  estilos["SubtituloOneToOne"]),
        Paragraph(
            f"Total de treinos no per\u00edodo: {len(treinos)}",
            estilos["Normal"]
        ),
        Spacer(1, 4)
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

    campos = [
        ("objetivos", "Objetivos"),
        ("tipo_treino", "Tipo de treino"),
        ("intensidade", "Intensidade"),
        ("desempenho", "Desempenho")
    ]

    def valor_disponivel(valor):
        if valor is None:
            return False
        texto = str(valor).strip()
        if not texto:
            return False
        return "dado ficticio de demonstracao" not in normalizar(texto)

    campos_exibidos = [
        campo for campo in campos
        if any(
            valor_disponivel(treino.get(campo[0]))
            for treino in treinos_exibidos
        )
    ]

    if treinos_exibidos:
        cabecalho = ["Data"] + [
            campo[1] for campo in campos_exibidos
        ]
        dados_treinos = [cabecalho]

        for treino in treinos_exibidos:
            linha = [
                escape(str(formatar_data(treino.get("data"))))
            ]

            for chave, nome in campos_exibidos:
                valor = treino.get(chave)
                texto = (
                    escape(str(valor))
                    if valor_disponivel(valor)
                    else "—"
                )
                linha.append(
                    Paragraph(texto, estilos["CelulaOneToOne"])
                )

            dados_treinos.append(linha)

        quantidade_colunas = len(cabecalho)
        largura_data = 3 * cm
        largura_restante = 16 * cm - largura_data
        largura_campo = largura_restante / max(
            quantidade_colunas - 1, 1
        )
        larguras = [largura_data] + [
            largura_campo
        ] * (quantidade_colunas - 1)

        conteudo.append(criar_tabela(
            dados_treinos,
            larguras,
            tamanho=8
        ))

        if not campos_exibidos:
            conteudo.extend([
                Spacer(1, 4),
                Paragraph(
                    "Os detalhes dos treinos, como objetivos, tipo "
                    "e desempenho, ainda não estão registrados "
                    "na base de dados.",
                    estilos["AvisoOneToOne"]
                )
            ])
    else:
        conteudo.append(Paragraph(
            "Nenhum treino registrado neste período.",
            estilos["AvisoOneToOne"]
        ))

    if periodo == "anual" and len(treinos) > 10:
        conteudo.extend([
            Spacer(1, 4),
            Paragraph(
                "São apresentados os 10 treinos mais recentes. "
                "O total considera todos os treinos do período.",
                estilos["AvisoOneToOne"]
            )
        ])

    documento.build(conteudo)

    print(f"PDF One to One gerado: {destino}")
    return destino


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de relatórios PKZ e One to One."
    )

    parser.add_argument(
        "atleta_id",
        nargs="?",
        help="ID do atleta na API ou nos JSON (opcional: usa o primeiro atleta PKZ)"
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

    parser.add_argument(
        "--json-dir",
        type=Path,
        help=(
            "Gera PKZ a partir de atleta.json e evolucao.json nesta pasta; "
            "presenca.json é opcional. Sem esta opção, consulta a API."
        ),
    )

    args = parser.parse_args()

    try:
        referencia = date.fromisoformat(args.referencia)
    except ValueError:
        parser.error("--referencia deve estar no formato YYYY-MM-DD")

    if args.one_to_one:
        if args.json_dir is not None:
            parser.error("--json-dir está disponível somente para relatórios PKZ.")
        if not args.atleta_id:
            parser.error("Informe atleta_id para gerar relatório One to One.")
        gerar_relatorio_one_to_one(
            args.atleta_id,
            args.periodo,
            referencia
        )
    else:
        gerar_relatorio(args.atleta_id, args.periodo, referencia, args.json_dir)


if __name__ == "__main__":
    main()
