
import json
import sys
from pathlib import Path
from io import BytesIO
from datetime import datetime
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)

# Caminhos do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
API_DIR = BASE_DIR / "exemplos" / "api"
SAIDA_DIR = BASE_DIR / "gerador_pkz" / "relatorios"


def carregar_json(nome):
    caminho = API_DIR / nome

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def normalizar(texto):
    texto = str(texto or "").lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )


def formatar_data(data):
    if not data:
        return "—"

    try:
        return datetime.strptime(
            data, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except ValueError:
        return str(data)


def formatar_valor(valor, unidade):
    if valor is None:
        return "—"

    if isinstance(valor, (int, float)):
        numero = (
            f"{valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        return f"{numero} {unidade or ''}".strip()

    return str(valor)


def formatar_percentual(valor):
    if valor is None:
        return "—"

    return f"{valor:+.1f}%".replace(".", ",")


def menor_e_melhor(codigo, nome):
    identificacao = normalizar(f"{codigo} {nome}")

    return (
        "sprint" in identificacao
        or "agilidade" in identificacao
        or "agility" in identificacao
    )


def criar_grafico(registros, nome_teste):
    confirmados = [
        item for item in registros
        if item.get("confirmado") is True
        and item.get("valor") is not None
    ]

    confirmados.sort(
        key=lambda item: item.get("data_avaliacao") or ""
    )

    if not confirmados:
        return None

    datas = [
        formatar_data(item.get("data_avaliacao"))
        for item in confirmados
    ]

    valores = [
        item["valor"] for item in confirmados
    ]

    unidade = confirmados[0].get(
        "unidade_medida", ""
    )

    figura, eixo = plt.subplots(figsize=(7, 3))

    eixo.plot(
        datas,
        valores,
        marker="o",
        linewidth=2
    )

    eixo.set_title(nome_teste, pad=10)

    eixo.set_ylabel(
        f"Resultado ({unidade})"
        if unidade else "Resultado"
    )

    eixo.set_xlabel("Data da avaliação")
    eixo.grid(True, linestyle="--", alpha=0.4)
    eixo.tick_params(axis="x", rotation=20)

    figura.tight_layout()

    imagem = BytesIO()

    figura.savefig(
        imagem,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(figura)
    imagem.seek(0)

    return imagem


def gerar_relatorio(atleta_id=None):
    atletas = carregar_json("atleta.json")
    comparacoes = carregar_json("comparacao.json")
    evolucoes = carregar_json("evolucao.json")

    if not atletas:
        raise ValueError(
            "O arquivo atleta.json não contém atletas."
        )

    if atleta_id:
        candidatos = [
            atleta for atleta in atletas
            if str(atleta.get("atleta_id")) == str(atleta_id)
        ]
    else:
        candidatos = [atletas[0]]

    if not candidatos:
        raise ValueError(
            f"Atleta não encontrado: {atleta_id}"
        )

    atleta = candidatos[0]
    atleta_id = atleta["atleta_id"]

    comparacoes = [
        item for item in comparacoes
        if str(item.get("atleta_id")) == str(atleta_id)
    ]

    evolucoes = [
        item for item in evolucoes
        if str(item.get("atleta_id")) == str(atleta_id)
    ]

    SAIDA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    destino = SAIDA_DIR / (
        f"relatorio_pkz_{atleta_id}.pdf"
    )

    estilos = getSampleStyleSheet()

    estilos.add(ParagraphStyle(
        name="TituloPKZ",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#176B55"),
        fontSize=22,
        spaceAfter=8
    ))

    estilos.add(ParagraphStyle(
        name="SubtituloPKZ",
        parent=estilos["Heading2"],
        textColor=colors.HexColor("#176B55"),
        spaceBefore=12,
        spaceAfter=8
    ))

    estilos.add(ParagraphStyle(
        name="AvisoPKZ",
        parent=estilos["Normal"],
        textColor=colors.HexColor("#555555"),
        fontSize=9,
        leading=12
    ))

    estilos.add(ParagraphStyle(
        name="NotaGraficoPKZ",
        parent=estilos["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#176B55"),
        fontSize=9,
        leading=12,
        spaceBefore=2,
        spaceAfter=8
    ))

    documento = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    conteudo = [
        Paragraph(
            "PKZ — Relatório de Evolução",
            estilos["TituloPKZ"]
        ),
        Paragraph(
            "Relatório gerado automaticamente a partir "
            "dos dados de avaliação.",
            estilos["Normal"]
        ),
        Spacer(1, 14),
        Paragraph(
            "Identificação do atleta",
            estilos["SubtituloPKZ"]
        )
    ]

    # Identificação enxuta, sem exibir o ID.
    identificacao = [
        ["Campo", "Informação"],
        ["Atleta", atleta.get("nome") or "Não informado"],
        ["Unidade", atleta.get("unidade") or "—"],
        ["Idade", str(atleta.get("idade") or "—")],
        ["Categoria", atleta.get("categoria") or "—"],
        [
            "Total de avaliações",
            str(atleta.get("total_avaliacoes", "—"))
        ],
        [
            "Última avaliação",
            formatar_data(
                atleta.get("ultima_avaliacao_em")
            )
        ]
    ]

    tabela = Table(
        identificacao,
        colWidths=[5 * cm, 11 * cm]
    )

    tabela.setStyle(TableStyle([
        (
            "BACKGROUND", (0, 0), (-1, 0),
            colors.HexColor("#176B55")
        ),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        (
            "BACKGROUND", (0, 1), (0, -1),
            colors.HexColor("#E8F4EF")
        ),
        (
            "GRID", (0, 0), (-1, -1),
            0.5, colors.HexColor("#C8D8D1")
        ),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    conteudo.extend([
        tabela,
        Spacer(1, 12)
    ])

    conteudo.append(
        Paragraph(
            "Avaliação atual x anterior",
            estilos["SubtituloPKZ"]
        )
    )

    linhas = [[
        "Teste",
        "Anterior",
        "Atual",
        "Variação",
        "Situação"
    ]]

    for item in comparacoes:
        unidade = item.get("unidade_medida", "")

        situacao_original = normalizar(
            item.get("situacao", "")
        )

        if item.get("confirmado") is False:
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
            situacao = item.get("situacao", "—")

        linhas.append([
            item.get(
                "teste_nome",
                item.get("teste", "—")
            ),
            formatar_valor(
                item.get("valor_anterior"), unidade
            ),
            formatar_valor(
                item.get("valor_atual"), unidade
            ),
            formatar_percentual(
                item.get("variacao_pct")
            ),
            situacao
        ])

    tabela_comparacao = Table(
        linhas,
        colWidths=[
            4.1 * cm,
            2.8 * cm,
            2.8 * cm,
            2.3 * cm,
            3.4 * cm
        ],
        repeatRows=1
    )

    tabela_comparacao.setStyle(TableStyle([
        (
            "BACKGROUND", (0, 0), (-1, 0),
            colors.HexColor("#176B55")
        ),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        (
            "GRID", (0, 0), (-1, -1),
            0.4, colors.HexColor("#C8D8D1")
        ),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        (
            "ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#F2F7F5")]
        ),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    conteudo.extend([
        tabela_comparacao,
        Spacer(1, 12)
    ])

    conteudo.append(
        Paragraph(
            "Evolução histórica por teste",
            estilos["SubtituloPKZ"]
        )
    )

    grupos = {}

    for registro in evolucoes:
        codigo = registro.get("teste", "outro")
        grupos.setdefault(codigo, []).append(registro)

    for codigo, registros in grupos.items():
        nome = registros[0].get(
            "teste_nome", codigo
        )

        grafico = criar_grafico(
            registros,
            nome
        )

        if grafico:
            elementos = [
                Paragraph(
                    nome,
                    estilos["Heading3"]
                ),
                Image(
                    grafico,
                    width=15 * cm,
                    height=6.4 * cm
                )
            ]

            # A indicação fica fora da imagem do gráfico,
            # em uma linha separada no próprio PDF.
            if menor_e_melhor(codigo, nome):
                elementos.append(
                    Paragraph(
                        "Menor tempo = melhor resultado",
                        estilos["NotaGraficoPKZ"]
                    )
                )

            elementos.append(Spacer(1, 8))
            conteudo.append(KeepTogether(elementos))

        else:
            conteudo.append(KeepTogether([
                Paragraph(
                    nome,
                    estilos["Heading3"]
                ),
                Paragraph(
                    "Gráfico disponível depois que a PKZ "
                    "validar este teste.",
                    estilos["AvisoPKZ"]
                ),
                Spacer(1, 8)
            ]))

    conteudo.append(Spacer(1, 10))

    conteudo.append(
        Paragraph(
            "Os resultados em validação não são apresentados "
            "como resultados confirmados nos gráficos.",
            estilos["Italic"]
        )
    )

    documento.build(conteudo)

    print(f"PDF gerado: {destino}")


if __name__ == "__main__":
    identificador = (
        sys.argv[1] if len(sys.argv) > 1 else None
    )

    gerar_relatorio(identificador)
