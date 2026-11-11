"""Renderização dos relatórios: HTML oficial (Jinja2) -> PDF (Playwright/Chromium).

Fluxo: dados da API -> contexto_relatorio -> template HTML -> Chromium -> PDF A4.
O gerador ReportLab de gerar_pdf.py continua disponível e é o padrão da CLI.
"""
import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from . import contexto_relatorio as cr

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
A4_LARGURA_PX = 793.7  # 210 mm a 96 dpi


@lru_cache(maxsize=None)
def _data_uri(subpasta, nome):
    caminho = TEMPLATES_DIR / subpasta / nome
    mime = mimetypes.guess_type(caminho.name)[0] or "font/ttf"
    if caminho.suffix == ".ttf":
        mime = "font/ttf"
    dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{dados}"


def _ambiente():
    ambiente = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"], default_for_string=True),
        undefined=StrictUndefined,
        trim_blocks=False,
    )
    # Fontes e imagens vão embutidas: o PDF não depende de internet nem do Google Fonts.
    ambiente.globals["asset"] = lambda nome: _data_uri("assets", nome)
    ambiente.globals["fonte"] = lambda nome: _data_uri("fonts", nome)
    return ambiente


def renderizar_html(contexto, incluir_extras=None, espaco=0):
    """HTML final do relatório (string), pronto para o Chromium.

    incluir_extras: ids dos blocos de apoio a incluir (None = todos).
    espaco: altura (px do layout) de um espaçador antes do rodapé, para encostá-lo no fim da página.
    """
    if incluir_extras is None:
        incluir_extras = [e["id"] for e in contexto.get("extras", [])]
    dados = {**contexto, "incluir_extras": list(incluir_extras), "espaco": int(espaco)}
    template = _ambiente().get_template(contexto["template"])
    return template.render(r=dados, **dados)


def html_para_pdf(html, destino, largura_px):
    """Converte o HTML em PDF A4 com fundos coloridos e fontes embutidas."""
    from playwright.sync_api import sync_playwright

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    escala = A4_LARGURA_PX / largura_px  # ajusta a largura do modelo à folha A4
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport={"width": int(largura_px), "height": 1200})
            pagina.set_content(html, wait_until="load")
            pagina.evaluate("document.fonts.ready.then(() => true)")
            pagina.pdf(
                path=str(destino),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                scale=escala,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            navegador.close()
    return destino


MARGEM_PT = 12 * 72 / 25.4  # margem inferior da folha (12 mm) em pontos
SEGURANCA_PX = 14  # folga para nunca empurrar o rodapé para uma página nova


def _opcoes_pdf(escala):
    return dict(format="A4", print_background=True, prefer_css_page_size=True, scale=escala,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})


def _y_do_texto(pagina_pdf, trecho):
    """Posição vertical (pontos, a partir da base da folha) da última ocorrência do texto na página."""
    achados = []

    def visitante(texto, cm, tm, _fonte, _tamanho):
        if trecho in texto:
            achados.append(tm[4] * cm[1] + tm[5] * cm[3] + cm[5])

    pagina_pdf.extract_text(visitor_text=visitante)
    return achados[-1] if achados else None


def _espaco_livre_px(pdf_bytes, rodape_abaixo_do_texto_px, escala):
    """Espaço vazio (px do layout) entre o rodapé e o fim da área útil da última página."""
    import io
    from pypdf import PdfReader

    ultima = PdfReader(io.BytesIO(pdf_bytes)).pages[-1]
    y_texto = _y_do_texto(ultima, "Armando")
    if y_texto is None:
        return 0
    y_base_rodape = y_texto - rodape_abaixo_do_texto_px * escala * 0.75
    return max(0.0, (y_base_rodape - MARGEM_PT) / 0.75 / escala)


def _paginas(pdf_bytes):
    import io
    from pypdf import PdfReader

    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def renderizar_pdf(contexto, destino):
    """PDF A4 do relatório: preenche o fim da última página com blocos de apoio e fixa o rodapé embaixo.

    Passagens: (1) conteúdo base; (2) mede o espaço livre e a altura de cada bloco de apoio, escolhe os
    que cabem, e (3) gera de novo com eles e um espaçador. Se a paginação mudar, mantém a passagem 1.
    """
    from playwright.sync_api import sync_playwright

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    largura = contexto["largura"]
    escala = A4_LARGURA_PX / largura
    extras = contexto.get("extras", [])

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport={"width": int(largura), "height": 1200})

            def carregar(html):
                pagina.set_content(html, wait_until="load")
                pagina.evaluate("document.fonts.ready.then(() => true)")

            carregar(renderizar_html(contexto, incluir_extras=[], espaco=0))
            base = pagina.pdf(**_opcoes_pdf(escala))
            final = base
            if extras:
                # distância do fundo do rodapé até a base do texto do endereço (layout contínuo)
                distancia = pagina.evaluate(
                    """() => { const f = document.querySelector('[data-rodape]');
                               const t = f.querySelectorAll('p')[1].getBoundingClientRect();
                               return f.getBoundingClientRect().bottom - (t.bottom - 3.5); }""")
                livre = _espaco_livre_px(base, distancia, escala) - SEGURANCA_PX

                carregar(renderizar_html(contexto, espaco=0))  # todos os blocos, só para medir
                alturas = pagina.evaluate(
                    """() => Object.fromEntries([...document.querySelectorAll('[data-extra]')]
                                .map(e => [e.dataset.extra, e.offsetHeight + 24]))""")
                escolhidos, restante = [], livre
                for e in extras:
                    h = alturas.get(e["id"], 0)
                    if h and h <= restante:
                        escolhidos.append(e["id"])
                        restante -= h
                if escolhidos or restante > 0:
                    carregar(renderizar_html(contexto, incluir_extras=escolhidos, espaco=max(0, int(restante))))
                    candidato = pagina.pdf(**_opcoes_pdf(escala))
                    if _paginas(candidato) == _paginas(base):
                        final = candidato
        finally:
            navegador.close()
    destino.write_bytes(final)
    return destino


def montar_contexto(unidade, atleta, periodo, referencia, evolucoes=None, presencas=None, treinos=None):
    """Seleciona e monta o contexto do relatório da unidade (None se sem dados)."""
    if cr.normalizar_unidade(unidade) == "ONE_TO_ONE":
        return cr.montar_contexto_one_to_one(atleta, presencas or [], treinos or [], periodo, referencia)
    return cr.montar_contexto_pkz(atleta, evolucoes or [], presencas or [], periodo, referencia)


def gerar_relatorio_html(unidade, atleta_id, periodo, referencia, json_dir=None, saida_dir=None):
    """Gera o PDF de um atleta a partir do template HTML. Retorna o caminho ou None sem dados."""
    from gerador_pkz import gerar_pdf as g

    unidade = cr.normalizar_unidade(unidade)
    inicio, fim = g.periodo_datas(periodo, referencia)
    if unidade == "ONE_TO_ONE":
        if json_dir is not None:
            raise ValueError("--json-dir está disponível somente para relatórios PKZ.")
        if not atleta_id:
            raise ValueError("Informe atleta_id para gerar relatório One to One.")
        atleta, presencas, treinos = g.carregar_dados_one_to_one(atleta_id, inicio, fim)
        contexto = montar_contexto(unidade, atleta, periodo, referencia, presencas=presencas, treinos=treinos)
    else:
        atleta, _comparacoes, evolucoes, presencas = g.buscar_dados_atleta(atleta_id, json_dir)
        contexto = montar_contexto(unidade, atleta, periodo, referencia, evolucoes=evolucoes, presencas=presencas)

    if contexto is None:
        print(f"Nenhum dado relevante no período {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}. PDF não gerado.")
        return None

    aid = atleta["atleta_id"] if "atleta_id" in atleta else atleta_id
    pasta = Path(saida_dir) if saida_dir else g.SAIDA_DIR
    nome = f"relatorio_html_{unidade.lower()}_{aid}_{periodo}_{referencia:%Y-%m-%d}.pdf"
    destino = renderizar_pdf(contexto, pasta / nome)
    print(f"PDF (HTML) gerado: {destino}")
    return destino
