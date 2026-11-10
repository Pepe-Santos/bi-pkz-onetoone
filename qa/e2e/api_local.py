"""Imita a API do Supabase lendo o PostgreSQL LOCAL do QA, para testar o gerador de PDF e o
envio em lote sem tocar no projeto real. Só a biblioteca padrão e o psql.

    python qa/e2e/api_local.py --porta 54321 --banco "postgresql://postgres@localhost/qa_local" --saida /tmp/bucket

Cobre só o que gerar_pdf.py e enviar_lote.py usam:
  GET  /rest/v1/<view>?coluna=eq.X&coluna=in.(A,B)&select=...&order=col.asc,col2
  POST /rest/v1/rpc/<funcao>           (corpo JSON com os argumentos)
  POST /storage/v1/object/<bucket>/<caminho>   (grava o arquivo em --saida)
Toda chamada roda como service_role (secret key), como no Supabase.
"""

import argparse
import json
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def literal(valor):
    return "'" + str(valor).replace("'", "''") + "'"


def ident(nome):
    if not IDENT.match(nome):
        raise ValueError(f"nome inválido: {nome}")
    return nome


def consultar(banco, sql):
    """Roda o SQL como service_role e devolve a lista JSON."""
    script = (
        "BEGIN;\n"
        "SELECT set_config('request.jwt.claims', '{\"role\":\"service_role\"}', true);\n"
        "SET LOCAL ROLE service_role;\n"
        f"SELECT coalesce(jsonb_agg(t), '[]')::text FROM ({sql}) t;\n"
        "COMMIT;\n"
    )
    saida = subprocess.run(["psql", banco, "-Atq", "-v", "ON_ERROR_STOP=1"], input=script,
                           capture_output=True, text=True)
    if saida.returncode:
        raise RuntimeError(saida.stderr.strip())
    linhas = [l for l in saida.stdout.splitlines() if l.startswith("[")]
    return json.loads(linhas[-1]) if linhas else []


def montar_select(view, params):
    colunas, filtros, ordem = "*", [], ""
    for chave, valor in params:
        if chave == "select":
            colunas = ", ".join(ident(c) for c in valor.split(","))
        elif chave == "order":
            partes = []
            for item in valor.split(","):
                col, _, direcao = item.partition(".")
                partes.append(f"{ident(col)} {'DESC' if direcao.startswith('desc') else 'ASC'}")
            ordem = " ORDER BY " + ", ".join(partes)
        else:
            op, _, alvo = valor.partition(".")
            if op == "eq":
                filtros.append(f"{ident(chave)}::text = {literal(alvo)}")
            elif op == "in":
                itens = alvo.strip("()").split(",")
                filtros.append(f"{ident(chave)}::text IN ({', '.join(literal(i) for i in itens)})")
            else:
                raise ValueError(f"operador não suportado: {op}")
    onde = " WHERE " + " AND ".join(filtros) if filtros else ""
    return f"SELECT {colunas} FROM api.{ident(view)}{onde}{ordem}"


class Handler(BaseHTTPRequestHandler):
    banco = ""
    saida = Path(".")

    def responder(self, codigo, corpo):
        dados = json.dumps(corpo, default=str).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        url = urlsplit(self.path)
        try:
            view = url.path.removeprefix("/rest/v1/")
            self.responder(200, consultar(self.banco, montar_select(view, parse_qsl(url.query))))
        except Exception as erro:
            self.responder(400, {"message": str(erro)})

    def do_POST(self):
        url = urlsplit(self.path)
        corpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            if url.path.startswith("/storage/v1/object/"):
                destino = self.saida / unquote(url.path.removeprefix("/storage/v1/object/"))
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(corpo)
                self.responder(200, {"Key": str(destino)})
            elif url.path.startswith("/rest/v1/rpc/"):
                funcao = ident(url.path.removeprefix("/rest/v1/rpc/"))
                args = json.loads(corpo or b"{}")
                lista = ", ".join(f"{ident(k)} => {literal(v)}" for k, v in args.items())
                self.responder(200, consultar(self.banco, f"SELECT * FROM api.{funcao}({lista})"))
            else:
                self.responder(404, {"message": "rota não suportada"})
        except Exception as erro:
            self.responder(400, {"message": str(erro)})

    def log_message(self, formato, *args):
        sys.stderr.write("[api_local] " + formato % args + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--porta", type=int, default=54321)
    parser.add_argument("--banco", required=True)
    parser.add_argument("--saida", default="qa/e2e/bucket_local")
    args = parser.parse_args()
    Handler.banco, Handler.saida = args.banco, Path(args.saida)
    print(f"API local em http://127.0.0.1:{args.porta}")
    ThreadingHTTPServer(("127.0.0.1", args.porta), Handler).serve_forever()


if __name__ == "__main__":
    main()
