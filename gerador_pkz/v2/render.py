"""Contrato validado -> HTML -> PDF A4, com conferência das folhas.

A conferência roda no próprio navegador que gera o PDF:
* o número de folhas é o do tipo (3, 4 ou 5);
* nenhum bloco tem conteúdo maior que o seu espaço (nada cortado nem sobreposto);
* nenhum gráfico sai da largura do bloco.
Se algo falhar, o PDF não é gravado e o erro diz em que folha e em que bloco.
"""
import base64
import mimetypes
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from . import PAGINAS
from . import contrato as C
from . import indicadores as I
from . import paginas as P

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
NOMES_ARQUIVO = {"PKZ": "PKZ", "ONE_TO_ONE": "OneToOne"}

CONFERIR = """() => {
  const problemas = [];
  document.querySelectorAll('.folha').forEach((f, i) => {
    if (f.scrollHeight > f.clientHeight + 1) problemas.push(`folha ${i + 1}: conteúdo maior que a folha`);
    f.querySelectorAll('.bloco').forEach(b => {
      const nome = (b.querySelector('h2') || {}).innerText || b.dataset.bloco;
      if (b.scrollHeight > b.clientHeight + 1) problemas.push(`folha ${i + 1}, bloco "${nome}": ${b.scrollHeight - b.clientHeight}px de conteúdo a mais na altura`);
      if (b.scrollWidth > b.clientWidth + 1) problemas.push(`folha ${i + 1}, bloco "${nome}": ${b.scrollWidth - b.clientWidth}px a mais na largura`);
      b.querySelectorAll('svg').forEach(s => { const r = s.getBoundingClientRect(), rb = b.getBoundingClientRect();
        if (r.right > rb.right + 1 || r.bottom > rb.bottom + 1) problemas.push(`folha ${i + 1}, bloco "${nome}": gráfico sai do bloco`); });
      b.querySelectorAll('td, .n, .mini b').forEach(c => { if (c.scrollWidth > c.clientWidth + 1 && getComputedStyle(c).textOverflow !== 'ellipsis')
        problemas.push(`folha ${i + 1}, bloco "${nome}": texto cortado`); });
    });
  });
  return {folhas: document.querySelectorAll('.folha').length, problemas};
}"""


@lru_cache(maxsize=None)
def _data_uri(subpasta, nome):
    caminho = TEMPLATES / subpasta / nome
    mime = "font/ttf" if caminho.suffix == ".ttf" else (mimetypes.guess_type(caminho.name)[0] or "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(caminho.read_bytes()).decode('ascii')}"


def _ambiente():
    amb = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "j2"]),
                      undefined=StrictUndefined)
    amb.globals["fonte"] = lambda nome: _data_uri("fonts", nome)
    return amb


def rotulo_periodo(tipo, inicio, fim):
    if tipo == "semanal":
        return f"{inicio:%d/%m} a {fim:%d/%m/%Y}"
    if tipo == "mensal":
        return f"{I.MESES[inicio.month - 1].capitalize()} de {inicio.year}"
    return str(inicio.year)


def montar_html(contrato, hoje=None):
    """HTML final e os indicadores usados (o contrato precisa estar validado)."""
    hoje = hoje or date.today()
    ind = I.calcular(contrato, hoje)
    paginas = P.montar(P.paginas(ind))
    tema = P.TEMAS[ind["modalidade"]]
    # One to One usa a paleta da PKZ: o modelo recebe "PKZ" para as duas unidades (cabeçalho, rodapé, resumo, tabelas).
    html = _ambiente().get_template("v2/relatorio.html").render(
        paginas=paginas, tema=tema, unidade="PKZ", titulo=P.TITULOS[ind["tipo"]],
        rotulo_periodo=rotulo_periodo(ind["tipo"], ind["inicio"], ind["fim"]), aluno_nome=ind["aluno"]["nome"],
        gerado_em=f"{hoje:%d/%m/%Y}", logo=_data_uri("assets", "logo_cabecalho.png" if ind["modalidade"] == "PKZ" else "logo_rodape.png"),
        geo={"corpo_a": P.CORPO_A, "margem_x": P.MARGEM_X, "margem_y": P.MARGEM_Y, "espaco": P.ESPACO, "pad": P.PAD,
             "cabecalho": P.CABECALHO, "rodape": P.RODAPE})
    return html, ind, paginas


class FolhasComProblema(Exception):
    pass


def gerar_pdf(contrato_bruto, destino, previas=None, hoje=None, tolerar_problemas=False):
    """Valida, gera e confere o PDF. Devolve (caminho do PDF, avisos da validação, problemas de layout)."""
    from playwright.sync_api import sync_playwright

    hoje = hoje or date.today()
    contrato, avisos = C.validar_ou_falhar(contrato_bruto, hoje)
    html, ind, paginas = montar_html(contrato, hoje)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        try:
            pagina = nav.new_page(viewport={"width": P.LARGURA, "height": P.ALTURA})
            pagina.set_content(html, wait_until="load")
            pagina.evaluate("document.fonts.ready.then(() => true)")
            conferencia = pagina.evaluate(CONFERIR)
            esperado = len(paginas)  # até PAGINAS[tipo]; menos quando os blocos sem dado saem
            problemas = list(conferencia["problemas"])
            if conferencia["folhas"] != esperado or esperado > PAGINAS[ind["tipo"]]:
                problemas.insert(0, f"{conferencia['folhas']} folhas montadas; o relatório {ind['tipo']} tem no máximo {PAGINAS[ind['tipo']]}.")
            if problemas and not tolerar_problemas:
                raise FolhasComProblema("\n".join(problemas))
            pdf = pagina.pdf(format="A4", print_background=True, prefer_css_page_size=True,
                             margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            from io import BytesIO
            from pypdf import PdfReader
            n = len(PdfReader(BytesIO(pdf)).pages)
            if n != esperado:
                raise FolhasComProblema(f"O PDF saiu com {n} páginas; o esperado eram {esperado}.")
            destino.write_bytes(pdf)
            if previas:
                previas = Path(previas)
                previas.mkdir(parents=True, exist_ok=True)
                for i, folha in enumerate(pagina.query_selector_all(".folha"), start=1):
                    folha.screenshot(path=str(previas / f"{destino.stem}_p{i}.png"))
        finally:
            nav.close()
    return destino, avisos, problemas


def nome_arquivo(contrato):
    ini = C.ler_data(contrato["periodo"]["inicio"])
    return f"{NOMES_ARQUIVO[C.MODALIDADES.get(str(contrato['modalidade']).upper(), 'PKZ')]}_relatorio_{contrato['tipo_relatorio']}_{ini:%Y-%m-%d}.pdf"
