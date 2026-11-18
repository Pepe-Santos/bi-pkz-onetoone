"""Comandos dos relatórios v2. Rode na raiz do repositório:

  python -m gerador_pkz.v2 modelo --modalidade PKZ --tipo mensal --saida dados/contrato.json
      Esqueleto vazio do contrato, para preencher à mão.

  python -m gerador_pkz.v2 validar dados/contrato.json
      Confere o contrato: erros (impedem o PDF) e avisos.

  python -m gerador_pkz.v2 exportar-api --modalidade PKZ --aluno <id> --tipo mensal --referencia 2026-08-15 \\
      --saida dados/contrato.json [--ficha "Ficha Matrícula_PKZ.csv.zip"] [--env caminho/.env] [--fotos pasta]
      Monta o contrato com os dados reais da API (e da ficha de matrícula, se o nome bater).
      A foto do cartão é <atleta_id>.jpg/.png na pasta de fotos (padrão: dados-reais/fotos/, fora do Git).

  python -m gerador_pkz.v2 importar-csv --pasta dados/csv --modalidade ONE_TO_ONE --tipo semanal \\
      --referencia 2026-08-24 --nome "Nome do aluno" --saida dados/contrato.json
      Monta o contrato a partir de sessoes.csv, avaliacoes.csv e treinos.csv.

  python -m gerador_pkz.v2 gerar dados/contrato.json --saida relatorios/saida [--previas relatorios/previas]
      Valida, gera e confere o PDF (3, 4 ou 5 páginas). Não grava nada se houver erro.

  python -m gerador_pkz.v2 alunos --modalidade ONE_TO_ONE [--env ...]
      Lista os alunos da API com a quantidade de registros, para escolher de quem gerar.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

from . import contrato as C


def _data(texto):
    d = C.ler_data(texto)
    if not d:
        raise argparse.ArgumentTypeError("use a data no formato AAAA-MM-DD")
    return d


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m gerador_pkz.v2", description="Relatórios PKZ e One to One (3, 4 e 5 páginas).")
    sub = p.add_subparsers(dest="comando", required=True)

    m = sub.add_parser("modelo", help="esqueleto vazio do contrato")
    m.add_argument("--modalidade", choices=["PKZ", "ONE_TO_ONE"], required=True)
    m.add_argument("--tipo", choices=C.TIPOS, required=True)
    m.add_argument("--saida", required=True)

    v = sub.add_parser("validar", help="confere um contrato")
    v.add_argument("arquivo")

    e = sub.add_parser("exportar-api", help="monta o contrato com os dados da API")
    e.add_argument("--modalidade", choices=["PKZ", "ONE_TO_ONE"], required=True)
    e.add_argument("--aluno", required=True, help="atleta_id")
    e.add_argument("--tipo", choices=C.TIPOS, required=True)
    e.add_argument("--referencia", type=_data, required=True, help="qualquer data dentro do período")
    e.add_argument("--saida", required=True)
    e.add_argument("--ficha", help="ficha de matrícula (CSV ou ZIP)")
    e.add_argument("--env", help="arquivo .env com as credenciais da API")
    e.add_argument("--fotos", help="pasta com as fotos dos alunos, <atleta_id>.jpg ou .png (padrão: dados-reais/fotos/)")

    i = sub.add_parser("importar-csv", help="monta o contrato a partir de CSVs")
    i.add_argument("--pasta", required=True)
    i.add_argument("--modalidade", choices=["PKZ", "ONE_TO_ONE"], required=True)
    i.add_argument("--tipo", choices=C.TIPOS, required=True)
    i.add_argument("--referencia", type=_data, required=True)
    i.add_argument("--nome", required=True)
    i.add_argument("--idade", type=int)
    i.add_argument("--ficha")
    i.add_argument("--saida", required=True)

    g = sub.add_parser("gerar", help="gera o PDF a partir de um contrato")
    g.add_argument("arquivo")
    g.add_argument("--saida", default="relatorios/saida")
    g.add_argument("--previas", help="pasta para imagens PNG de cada página")

    a = sub.add_parser("alunos", help="lista os alunos da API")
    a.add_argument("--modalidade", choices=["PKZ", "ONE_TO_ONE"], required=True)
    a.add_argument("--env")

    args = p.parse_args(argv)
    if args.comando == "modelo":
        print(f"Modelo salvo em {C.salvar(C.modelo_vazio(args.modalidade, args.tipo), args.saida)}")
        return 0
    if args.comando == "validar":
        try:
            bruto = C.carregar(args.arquivo)
        except C.ContratoInvalido as erro:
            print("ERRO:", erro)
            return 1
        _, erros, avisos = C.validar(bruto)
        for x in erros:
            print("ERRO:", x)
        for x in avisos:
            print("AVISO:", x)
        print("Contrato válido." if not erros else f"{len(erros)} erro(s): o relatório não pode ser gerado.")
        return 1 if erros else 0
    if args.comando == "exportar-api":
        from . import fontes
        c = fontes.exportar_da_api(args.modalidade, args.aluno, args.tipo, args.referencia, args.env, args.ficha, fotos=args.fotos)
        foto = "com foto" if c["aluno"].get("foto") else f"sem foto em {fontes.pasta_de_fotos(args.fotos)}"
        print(f"Contrato salvo em {C.salvar(c, args.saida)} (ficha: {c['origem'].get('ficha', 'não informada')}; {foto}).")
        return 0
    if args.comando == "importar-csv":
        from . import fontes
        c = fontes.importar_csv(args.pasta, args.modalidade, args.tipo, args.referencia.isoformat(), {"nome": args.nome, "idade": args.idade})
        if args.ficha:
            fontes.aplicar_ficha(c, args.ficha)
        print(f"Contrato salvo em {C.salvar(c, args.saida)}.")
        return 0
    if args.comando == "gerar":
        from . import render
        try:
            bruto = C.carregar(args.arquivo)
            destino = Path(args.saida) / render.nome_arquivo(C.validar(bruto)[0] or bruto)
            pdf, avisos, _ = render.gerar_pdf(bruto, destino, previas=args.previas)
        except (C.ContratoInvalido, render.FolhasComProblema) as erro:
            for x in getattr(erro, "erros", [str(erro)]):
                print("ERRO:", x)
            return 1
        for x in avisos:
            print("AVISO:", x)
        print(f"PDF gerado: {pdf}")
        return 0
    if args.comando == "alunos":
        from . import fontes
        for x in fontes.listar_alunos(args.modalidade, args.env):
            print(f"{x['atleta_id']}  {x.get('nome')}  ({x.get('idade') or '—'} anos, {x.get('total_avaliacoes') or 0} avaliações)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
