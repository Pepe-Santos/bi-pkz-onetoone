import argparse
import os
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

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
    if isinstance(valor, (int, float)):
        numero = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{numero} {unidade or ''}".strip()
    return str(valor)


def formatar_percentual(valor):
    if valor is None:
        return "—"
    return f"{valor:+.1f}%".replace(".", ",")


def menor_e_melhor(codigo, nome):
    identificacao = normalizar(f"{codigo} {nome}")
    return "sprint" in identificacao or "agilidade" in identificacao or "agility" in identificacao


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
        return f"Relatório semanal · {inicio:%d/%m} a {fim:%d/%m/%Y}"
    if periodo == "mensal":
        return f"Relatório mensal · {inicio:%m/%Y}"
    return f"Relatório anual · {inicio:%Y}"


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
        fontName="Helvetica",
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
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
    atleta, comparacoes, evolucoes, presencas = buscar_dados_atleta(atleta_id)
    aid = atleta["atleta_id"]

    evolucoes_periodo = []
    avaliacoes_ids = set()
    for registro in evolucoes:
        try:
            data_avaliacao = date.fromisoformat(str(registro.get("data_avaliacao"))[:10])
        except (TypeError, ValueError):
            continue
        if inicio <= data_avaliacao <= fim:
            evolucoes_periodo.append(registro)
            if registro.get("avaliacao_id"):
                avaliacoes_ids.add(registro["avaliacao_id"])

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

    estilos = getSampleStyleSheet()
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
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
        situacao_original = normalizar(item.get("situacao", ""))
        # Só classifica como melhorou/piorou/estável quando confirmado for exatamente True.
        if item.get("confirmado") is not True:
            situacao = "Em validação"
        elif situacao_original == "melhorou":
            situacao = "Melhorou"
        elif situacao_original == "estavel":
            situacao = "Estável"
        elif situacao_original == "piorou":
            situacao = "Piorou"
        elif situacao_original == "sem_comparacao":
            situacao = "Sem comparação"
        else:
            situacao = item.get("situacao", "—") or "—"
        linhas.append([
            item.get("teste_nome", item.get("teste", "—")),
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
    for registro in evolucoes:
        codigo = registro.get("teste", "outro")
        grupos[codigo].append(registro)
    for codigo, registros in grupos.items():
        nome = registros[0].get("teste_nome", codigo)
        grafico = criar_grafico(registros, nome)
        if grafico:
            elementos = [Paragraph(nome, estilos["Heading3"]), Image(grafico, width=15 * cm, height=6.4 * cm)]
            if menor_e_melhor(codigo, nome):
                elementos.append(Paragraph("Menor tempo = melhor resultado", estilos["NotaGraficoPKZ"]))
            elementos.append(Spacer(1, 8))
            conteudo.append(KeepTogether(elementos))
        else:
            conteudo.append(KeepTogether([
                Paragraph(nome, estilos["Heading3"]),
                Paragraph("Gráfico disponível depois que a PKZ validar este teste.", estilos["AvisoPKZ"]),
                Spacer(1, 8),
            ]))
    conteudo.extend([
        Spacer(1, 10),
        Paragraph("Os resultados em validação não são apresentados como resultados confirmados nos gráficos.", estilos["Italic"]),
    ])
    documento.build(conteudo)
    print(f"PDF gerado: {destino}")
    return destino


def main():
    parser = argparse.ArgumentParser(description="Gera relatório de evolução PKZ usando a API do Supabase.")
    parser.add_argument("atleta_id", help="ID do atleta na API do Supabase")
    parser.add_argument("--periodo", choices=["semanal", "mensal", "anual"], default="mensal")
    parser.add_argument("--referencia", default=(date.today() - timedelta(days=1)).isoformat(),
                        help="Data de referência no formato YYYY-MM-DD (padrão: ontem)")
    args = parser.parse_args()
    try:
        referencia = date.fromisoformat(args.referencia)
    except ValueError as exc:
        parser.error("--referencia deve estar no formato YYYY-MM-DD")
    gerar_relatorio(args.atleta_id, args.periodo, referencia)


if __name__ == "__main__":
    main()
