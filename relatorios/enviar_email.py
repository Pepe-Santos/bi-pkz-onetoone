"""Envia um relatório em PDF por e-mail, pelo SMTP do Gmail.

Primeiro passo do envio automático dos relatórios: a tarefa seguinte chama a
enviar_email() para cada aluno. Lê do backend/.env (veja backend/env.example):

    EMAIL_USUARIO      conta Gmail do projeto
    EMAIL_SENHA_APP    senha de app dessa conta (não é a senha normal)
    EMAILS_TESTE       e-mails do grupo que podem receber, separados por vírgula

Modo teste: só envia para os endereços de EMAILS_TESTE. Qualquer outro destinatário
é recusado com um aviso. Nenhum endereço do banco é usado até a PKZ autorizar.

    python relatorios/enviar_email.py [caminho_do_pdf]

Sem argumento, manda o PDF de exemplo do gerador_pkz (python gerador_pkz/gerar_pdf.py)
para todos os e-mails de EMAILS_TESTE.
"""

import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "backend" / ".env"
PDF_EXEMPLO_DIR = BASE_DIR / "gerador_pkz" / "relatorios"

SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PORTA = 465

# Textos dos e-mails: um para os pais (PKZ) e um para o aluno (One to One).
# {nome} é o primeiro nome do atleta/aluno; {periodo} é semanal, mensal ou anual.
TEXTOS = {
    "PKZ": {
        "assunto": "Relatório {periodo} de {nome} — Playmakerz Lab",
        "corpo": (
            "Olá, família de {nome}!\n\n"
            "Segue em anexo o relatório {periodo} com a evolução de {nome} "
            "nos testes físicos da Playmakerz Lab.\n\n"
            "Os resultados ainda em validação aparecem marcados no relatório "
            "e não entram nos gráficos.\n\n"
            "Qualquer dúvida, é só responder este e-mail ou falar com o treinador.\n\n"
            "Equipe PKZ"
        ),
    },
    "ONE_TO_ONE": {
        "assunto": "Seu relatório {periodo} de treinos — One to One Studio",
        "corpo": (
            "Olá, {nome}!\n\n"
            "Segue em anexo o seu relatório {periodo} de treinos no One to One Studio, "
            "com o histórico, as cargas e a sua progressão no período.\n\n"
            "Se quiser conversar sobre os resultados, fale com o seu personal "
            "na próxima sessão.\n\n"
            "Equipe One to One Studio"
        ),
    },
}


def montar_texto(unidade, nome, periodo):
    """Devolve (assunto, corpo) do e-mail da unidade (PKZ ou ONE_TO_ONE)."""
    texto = TEXTOS[unidade]
    return (
        texto["assunto"].format(nome=nome, periodo=periodo),
        texto["corpo"].format(nome=nome, periodo=periodo),
    )


def emails_teste():
    """Lista fixa de quem pode receber no modo teste (EMAILS_TESTE do .env)."""
    load_dotenv(ENV_PATH)
    return {
        email.strip().lower()
        for email in os.environ.get("EMAILS_TESTE", "").split(",")
        if email.strip()
    }


def enviar_email(destinatario, assunto, corpo, caminho_pdf):
    """Envia o PDF anexo. Devolve True se enviou e False se o modo teste recusou."""
    load_dotenv(ENV_PATH)
    faltando = [nome for nome in ("EMAIL_USUARIO", "EMAIL_SENHA_APP")
                if not os.environ.get(nome)]
    if faltando:
        raise RuntimeError(f"Faltam variáveis no backend/.env: {', '.join(faltando)}")

    if destinatario.strip().lower() not in emails_teste():
        print(f"[modo teste] {destinatario} não está em EMAILS_TESTE; e-mail não enviado.")
        return False

    pdf = Path(caminho_pdf)
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {pdf}")

    usuario = os.environ["EMAIL_USUARIO"]
    mensagem = EmailMessage()
    mensagem["From"] = usuario
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)
    mensagem.add_attachment(
        pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name
    )

    with smtplib.SMTP_SSL(SMTP_SERVIDOR, SMTP_PORTA, context=ssl.create_default_context()) as smtp:
        smtp.login(usuario, os.environ["EMAIL_SENHA_APP"].replace(" ", ""))
        smtp.send_message(mensagem)

    print(f"Enviado para {destinatario}: {pdf.name}")
    return True


def pdf_de_exemplo():
    pdfs = sorted(PDF_EXEMPLO_DIR.glob("relatorio_pkz_*.pdf"))
    if not pdfs:
        sys.exit("Nenhum PDF de exemplo. Gere um com: python gerador_pkz/gerar_pdf.py")
    return pdfs[0]


def main():
    caminho_pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else pdf_de_exemplo()
    destinatarios = sorted(emails_teste())
    if not destinatarios:
        sys.exit("EMAILS_TESTE está vazio no backend/.env.")

    assunto, corpo = montar_texto("PKZ", "Atleta Exemplo", "mensal")
    assunto = f"[TESTE] {assunto}"
    enviados = sum(enviar_email(email, assunto, corpo, caminho_pdf) for email in destinatarios)
    print(f"{enviados} de {len(destinatarios)} e-mail(s) enviados.")


if __name__ == "__main__":
    main()
