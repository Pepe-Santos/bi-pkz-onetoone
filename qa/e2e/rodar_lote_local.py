"""Roda o relatorios/enviar_lote.py contra a API local (qa/e2e/api_local.py), trocando o SMTP
do Gmail por um falso que só guarda as mensagens. Nenhum e-mail sai da máquina.

    SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_SECRET_KEY=x \\
    python qa/e2e/rodar_lote_local.py --periodo mensal --referencia 2026-08-20 [--limite 2] [--simular]

No fim, mostra o que teria sido enviado (destinatário, assunto e anexo) e salva um resumo
em qa/e2e/saida/emails.json (só UUID e assunto; os PDFs ficam fora do git).
"""

import json
import os
import smtplib
import sys
from pathlib import Path

RAIZ = Path(os.environ.get("REPO_LOTE", Path(__file__).resolve().parents[2]))
SAIDA = Path(__file__).resolve().parent / "saida"
ENVIADOS = []


class SMTPFalso:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, usuario, senha):
        pass

    def send_message(self, mensagem):
        anexos = [p.get_filename() for p in mensagem.walk() if p.get_filename()]
        ENVIADOS.append({"para": mensagem["To"], "de": mensagem["From"],
                         "assunto": mensagem["Subject"], "anexos": anexos})


smtplib.SMTP_SSL = SMTPFalso
os.environ.setdefault("EMAIL_USUARIO", "projeto.qa@example.com")
os.environ.setdefault("EMAIL_SENHA_APP", "senha-falsa")
os.environ.setdefault("EMAILS_TESTE", "grupo.qa@example.com")
os.environ.setdefault("EMAIL_LOTE_TESTE", "grupo.qa@example.com")

sys.path.insert(0, str(RAIZ / "relatorios"))
import enviar_lote  # noqa: E402

codigo = 0
try:
    enviar_lote.main()
except SystemExit as saida:
    codigo = saida.code or 0
finally:
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "emails.json").write_text(json.dumps(ENVIADOS, ensure_ascii=False, indent=2))
    for email in ENVIADOS:
        print(f"  [smtp falso] para {email['para']} | {email['assunto']} | anexos: {email['anexos']}")
    print(f"  código de saída: {codigo}")
sys.exit(codigo)
